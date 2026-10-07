"""Single-owner v2 serial transports. No implicit fault acknowledgement or motion retry."""
from concurrent.futures import Future
from dataclasses import dataclass, field
import queue
import threading
import time
import serial


@dataclass
class BoardState:
    role: str
    identified: bool = False
    connected: bool = False
    telemetry: dict = field(default_factory=dict)
    error: str = ""
    ir_events: int = 0
    last_reply: float = 0.0


class BoardLink:
    def __init__(self, role, port, on_failure=lambda reason: None, serial_factory=None):
        self.role, self.port = role, port
        self.on_failure, self.serial_factory = on_failure, serial_factory
        self.state = BoardState(role)
        self._lock = threading.Lock()
        self._queue = queue.Queue(maxsize=8)
        self._stop = threading.Event()
        self._halt = threading.Event()
        self._thread = None
        self._pending = None
        self._next_id = 1
        self._status_complete = False
        self._status_at = 0.0
        self._command_values = {}

    def snapshot(self):
        with self._lock:
            return BoardState(**{**vars(self.state), "telemetry": dict(self.state.telemetry)})

    def start(self):
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Board worker is already running")
        if not self.port:
            raise ValueError(f"Select the {self.role.lower()} port")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"OvaLens-{self.role}")
        self._thread.start()

    def stop(self):
        self.halt()
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)

    def halt(self):
        # Priority signal cannot be trapped behind a full command queue.
        self._halt.set()

    def command(self, text, timeout=3):
        if "\n" in text or "\r" in text or len(text) > 65:
            raise ValueError("Invalid board command")
        state = self.snapshot()
        if not state.connected or not state.identified or not self._status_complete or state.error:
            raise RuntimeError(state.error or f"{self.role} handshake is incomplete")
        future = Future()
        future.deadline = time.monotonic() + timeout
        self._queue.put_nowait((text, timeout, future))
        return future

    def _cancel(self, reason):
        if self._pending:
            future = self._pending[3]
            if not future.done():
                future.set_exception(RuntimeError(reason))
            self._pending = None
        while True:
            try:
                _, _, future = self._queue.get_nowait()
                future.set_exception(RuntimeError(reason))
            except queue.Empty:
                break

    def _fail(self, reason):
        with self._lock:
            already_failed = bool(self.state.error)
            self.state.error = reason
            self.state.identified = False
        self._status_complete = False
        self._stop.set()
        self._cancel(reason)
        if not already_failed:
            self.on_failure(f"{self.role}: {reason}")

    def _receive(self, line, now):
        ident, payload = None, line
        if line.startswith("ID:"):
            parts = line.split(":", 2)
            if len(parts) != 3 or not parts[1].isdigit():
                self._fail("Malformed correlated reply")
                return
            ident, payload = int(parts[1]), parts[2]
        with self._lock:
            self.state.last_reply = now
        if ident is not None and (not self._pending or ident != self._pending[0]):
            return  # Late command telemetry must not replace current position or fault state.
        if payload.startswith("BOOT:"):
            if self._status_complete:
                self._fail("Board reset; inspect and reconnect")
            return
        if payload.startswith("READY:"):
            expected = f"READY:{self.role}_V2:PROTOCOL=2"
            if payload != expected:
                self._fail("Board role or protocol mismatch")
            else:
                with self._lock:
                    self.state.identified = True
            return
        if payload.startswith("ERROR:"):
            if ident is None or (self._pending and ident == self._pending[0]):
                self._fail(payload)
            return
        key, sep, value = payload.partition(":")
        if key == "FAULT" and value.startswith("STARTUP") and self.snapshot().telemetry.get("FAULT") == "NONE":
            self._fail("Board reset; inspect and reconnect")
            return
        if sep and key not in {"OK", "PONG", "EVENT"}:
            with self._lock:
                self.state.telemetry[key] = value
            if key == "LAST_ID" and value.isdigit():
                self._next_id = max(self._next_id, int(value) + 1)
        if payload.startswith("EVENT:IR:"):
            with self._lock:
                self.state.ir_events += 1
            if self._pending and ident == self._pending[0]:
                if "IR_EVENT" in self._command_values:
                    self._fail("Multiple IR events for one indexed move")
                    return
                self._command_values["IR_EVENT"] = value
        if ident is None and key == "STATE" and self.snapshot().identified:
            self._status_complete = True
            self._status_at = now
        if self._pending and ident == self._pending[0]:
            if sep and key not in {"OK", "EVENT"}:
                self._command_values[key] = value
            if payload in {"OK:MOVE_DONE", "OK:SERVO_DONE", "OK:FAULT_ACKNOWLEDGED", "OK:HOME_SET",
                           "OK:SPEED", "OK:PRESET_SET", "OK:IR_CONFIG", "OK:STATION_SET"}:
                self._pending[4] = True
            # STATE is the final line of the matching command report.
            if key == "STATE" and self._pending[4]:
                future = self._pending[3]
                self._pending = None
                future.set_result(dict(self._command_values))

    def _run(self):
        connection = None
        try:
            factory = self.serial_factory or getattr(serial, "Serial", None)
            if factory is None:
                raise RuntimeError("PySerial is unavailable; install the edge requirements (pyserial)")
            connection = factory(self.port, 115200, timeout=.02, write_timeout=.2)
            with self._lock:
                self.state.connected = True
                self.state.last_reply = time.monotonic()
            # Opening an ESP32 port can reset it; wait for its boot without motion.
            started, heartbeat = time.monotonic(), 0.0
            buffer = bytearray()
            while not self._stop.is_set():
                now = time.monotonic()
                if self._halt.is_set():
                    self._halt.clear()
                    self._cancel("Stopped; physical reconciliation required")
                    connection.write(b"ESTOP\n")
                if now - heartbeat >= .5:
                    connection.write(b"STATUS\n" if self.snapshot().identified else b"HELLO\n")
                    heartbeat = now
                if now - self.snapshot().last_reply > 2 or (not self._status_complete and now - started > 5):
                    raise RuntimeError("Board response timeout")
                if self._pending and now > self._pending[2]:
                    raise RuntimeError("Command completion timeout; do not retry motion")
                if not self._pending and self._status_complete and not self.snapshot().error:
                    try:
                        text, timeout, future = self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        ident = self._next_id
                        if future.cancelled() or now >= future.deadline:
                            if not future.done():
                                future.set_exception(RuntimeError("Command expired before dispatch"))
                            raise RuntimeError("Command expired before dispatch; inspect before retry")
                        if ident > 2147483647:
                            raise RuntimeError("Command ID exhausted; reconnect after inspection")
                        self._next_id += 1
                        self._pending = [ident, text, min(now + timeout, future.deadline), future, False]
                        self._command_values = {}
                        connection.write(f"@{ident} {text}\n".encode("ascii"))
                chunk = connection.read(256)
                for byte in chunk:
                    if byte == 10:
                        self._receive(buffer.decode("ascii", errors="strict").strip(), time.monotonic())
                        buffer.clear()
                    elif byte != 13:
                        buffer.append(byte)
                        if len(buffer) > 256:
                            raise RuntimeError("Oversized board reply")
        except Exception as exc:
            self._fail(str(exc))
        finally:
            if connection:
                try:
                    connection.write(b"ESTOP\n")
                except Exception:
                    pass
                connection.close()
            self._cancel("Board disconnected")
            with self._lock:
                self.state.connected = self.state.identified = False


class DualBoardController:
    def __init__(self, conveyor_port, servo_port, serial_factory=None):
        if not conveyor_port or not servo_port or conveyor_port == servo_port:
            raise ValueError("Select two different serial ports")
        self.failure = ""
        self.conveyor = BoardLink("CONVEYOR", conveyor_port, self._failure, serial_factory)
        self.servo = BoardLink("SERVO", servo_port, self._failure, serial_factory)

    def _failure(self, reason):
        self.failure = reason
        self.halt()

    def start(self):
        self.conveyor.start()
        self.servo.start()

    def halt(self):
        self.conveyor.halt()
        self.servo.halt()

    def stop(self):
        self.halt()
        self.conveyor.stop()
        self.servo.stop()

    def require_ready(self):
        if self.failure:
            raise RuntimeError(self.failure)
        for link in (self.conveyor, self.servo):
            state = link.snapshot()
            if not state.connected or not state.identified or state.error or not link._status_complete:
                raise RuntimeError(f"{link.role} is not ready")
            if state.telemetry.get("FAULT") != "NONE" or state.telemetry.get("BUSY") != "0":
                raise RuntimeError(f"{link.role} requires idle fault acknowledgement")
        state = self.conveyor.snapshot()
        if state.telemetry.get("REFERENCE_VALID") != "1" or state.telemetry.get("IR_CAPABLE") != "1":
            raise RuntimeError("Conveyor needs a reference and chamber IR firmware")
