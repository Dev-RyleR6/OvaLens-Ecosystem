"""Two-board prototype protocol, isolated from the GUI and production driver."""

from dataclasses import dataclass
from collections import OrderedDict
import queue
import threading
import time

import serial


def choose_port(available, current="", preferred="", used=()):
    """Preserve explicit choices; assign distinct initial ports for two boards."""
    if current and current != "No ports":
        return current
    if preferred:
        return preferred
    return next((port for port in available if port not in used), "No ports")


def egg_status(busy, automatic):
    """Interpret the deployed conveyor's STATUS flags without inventing movement."""
    if automatic == "1":
        return "AUTO_RUNNING"
    if busy == "1":
        return "MOVING"
    if busy == "0" and automatic == "0":
        return "IDLE"
    return "RESPONDING"


def integer(value, minimum, maximum, label):
    """Validate operator input without silently clamping mechanical settings."""
    text = str(value).strip()
    try:
        number = int(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return number


def validate_command(role, command):
    """Allow only commands supported by the original standalone controllers."""
    simple = {
        "egg": {"START", "STOP", "HOME", "STATUS", "SETHOME", "SETCHAMBER",
                "SETOUTPUT", "GOTO:CHAMBER", "GOTO:OUTPUT"},
        "servo": {"STATUS", "RESET", "SORT:FERTILE", "SORT:INFERTILE"},
    }
    numeric = {
        "egg": {"SPEED": (200, 5000), "JOG": (-100000, 100000),
                "TEST": (1, 100000)},
        "servo": {"SERVO": (0, 180), "SET_FERTILE": (0, 180),
                  "SET_INFERTILE": (0, 180)},
    }
    if role not in simple or not isinstance(command, str):
        raise ValueError("Unknown controller or command.")
    if command in simple[role]:
        return command
    prefix, separator, value = command.partition(":")
    if separator and prefix in numeric[role]:
        low, high = numeric[role][prefix]
        return f"{prefix}:{integer(value, low, high, prefix)}"
    raise ValueError(f"Unsupported {role} command: {command!r}")


@dataclass(frozen=True)
class ControllerEvent:
    role: str
    kind: str
    value: str


class SimulatedBoard:
    """Explicit simulation of the legacy protocols; no serial ports are opened."""

    def __init__(self, role):
        self.role = role
        self.position = 0
        self.chamber = 200
        self.output = 500
        self.speed = 800
        self.angle = 90
        self.fertile = 30
        self.infertile = 90
        self.state = "HOME" if role == "egg" else "NEUTRAL"
        self.running = False
        self.phase = 0
        self.next_step = 0.0

    def execute(self, command):
        command = validate_command(self.role, command)
        prefix, _, value = command.partition(":")
        if self.role == "servo":
            if prefix == "SERVO":
                self.angle, self.state = int(value), "MANUAL"
            elif prefix == "SET_FERTILE":
                self.fertile = int(value)
            elif prefix == "SET_INFERTILE":
                self.infertile = int(value)
            elif prefix == "SORT":
                self.angle = self.fertile if value == "FERTILE" else self.infertile
                self.state = value
            elif command == "RESET":
                self.angle, self.state = 90, "NEUTRAL"
            return [f"ANGLE:{self.angle}", f"FERTILE:{self.fertile}",
                    f"INFERTILE:{self.infertile}", f"STATE:{self.state}"]
        if command == "START":
            self.running, self.phase, self.next_step = True, 0, time.monotonic() + 1
            self.state = "AUTO_RUNNING"
        elif command in {"STOP", "HOME"}:
            self.running, self.position = False, 0
            self.state = "STOPPED" if command == "STOP" else "HOME"
        elif command == "SETHOME":
            if self.running:
                return ["ERROR:SYSTEM_BUSY"]
            self.position = 0
        elif command == "SETCHAMBER":
            self.chamber = self.position
        elif command == "SETOUTPUT":
            self.output = self.position
        elif prefix in {"JOG", "GOTO", "TEST"}:
            if self.running:
                return ["ERROR:SYSTEM_BUSY"]
            if prefix == "TEST" and self.position != 0:
                return ["ERROR:TEST_REQUIRES_HOME"]
            if prefix == "JOG":
                self.position += int(value)
            elif prefix == "TEST":
                self.position = int(value)
            else:
                self.position = self.chamber if value == "CHAMBER" else self.output
            self.state = "TEST_COMPLETE" if prefix == "TEST" else "IDLE"
        elif prefix == "SPEED":
            self.speed = int(value)
        return [f"POSITION:{self.position}", f"CHAMBER:{self.chamber}",
                f"OUTPUT:{self.output}", f"SPEED:{self.speed}", f"STATE:{self.state}"]

    def tick(self):
        if not self.running or time.monotonic() < self.next_step:
            return []
        self.position = (self.chamber, self.output, 0)[self.phase]
        self.state = ("AT_CHAMBER", "AT_OUTPUT", "AUTO_RUNNING")[self.phase]
        self.phase = (self.phase + 1) % 3
        self.next_step = time.monotonic() + 1
        return [f"POSITION:{self.position}", f"STATE:{self.state}"]


class EventInbox:
    """Bound UI backlog and collapse superseded numeric serial telemetry."""

    TELEMETRY = {"POSITION", "CHAMBER", "OUTPUT", "SPEED", "ANGLE", "FERTILE",
                 "INFERTILE", "BUSY", "AUTO", "NEUTRAL"}

    def __init__(self, capacity=2000):
        self.capacity = capacity
        self._items = OrderedDict()
        self._lock = threading.Lock()
        self._sequence = 0
        self.dropped = 0

    def put(self, event):
        with self._lock:
            self._sequence += 1
            key = ("event", self._sequence)
            if isinstance(event, ControllerEvent) and event.kind == "rx":
                prefix = event.value.partition(":")[0]
                if prefix in self.TELEMETRY:
                    key = (event.role, prefix)
            self._items[key] = event
            self._items.move_to_end(key)
            if len(self._items) > self.capacity:
                self._items.popitem(last=False)
                self.dropped += 1

    def get_nowait(self):
        with self._lock:
            if not self._items:
                raise queue.Empty
            return self._items.popitem(last=False)[1]


class OpticalCounter:
    """Count actual optical events using the firmware's 600 ms lockout."""

    def __init__(self):
        self.count = 0
        self.last = float("-inf")

    def feed(self, line, now=None):
        now = time.monotonic() if now is None else now
        if line != "EVENT:EGG_DETECTED" or now - self.last < 0.6:
            return False
        self.count += 1
        self.last = now
        return True


class SerialLink:
    """One worker owns all port I/O; events are consumed on the Tk main thread."""

    def __init__(self, role, events, serial_factory=serial.Serial, boot_seconds=2.0):
        self.role = role
        self.events = events
        self.serial_factory = serial_factory
        self.boot_seconds = boot_seconds
        self.ready = False
        self.port = ""
        self.simulated = False
        self._commands = queue.Queue(maxsize=100)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._epoch = 0

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    def emit(self, kind, value):
        self.events.put(ControllerEvent(self.role, kind, value))

    def connect(self, port, simulated=False):
        if self.active:
            raise ValueError(f"The {self.role} controller is already connecting or connected.")
        if not simulated and not port.strip():
            raise ValueError(f"Select the {self.role} controller's COM port.")
        self.port, self.simulated = port.strip(), simulated
        self.ready = False
        self._stop.clear()
        self._discard_commands()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name=f"OvaLens-Prototype-{self.role}")
        self._thread.start()

    def _discard_commands(self):
        while True:
            try:
                self._commands.get_nowait()
            except queue.Empty:
                return

    def send_many(self, commands, priority=False):
        validated = tuple(validate_command(self.role, cmd) for cmd in commands)
        with self._lock:
            if not self.ready or self._stop.is_set():
                raise ValueError(f"Connect the {self.role} controller first.")
            if priority:
                self._epoch += 1
                self._discard_commands()
            try:
                self._commands.put_nowait((self._epoch, validated))
            except queue.Full as exc:
                raise ValueError("Controller command queue is full; wait or stop.") from exc

    def send(self, command, priority=False):
        self.send_many([command], priority)

    def disconnect(self):
        with self._lock:
            self.ready = False
            self._epoch += 1
            self._stop.set()
            self._discard_commands()

    def _run(self):
        connection = None
        board = None
        connected = False
        pending = bytearray()
        self.emit("connection", "CONNECTING")
        try:
            if self.simulated:
                board = SimulatedBoard(self.role)
            else:
                connection = self.serial_factory(port=self.port, baudrate=115200,
                                                  timeout=0.02, write_timeout=0.25)
                if self._stop.wait(self.boot_seconds):
                    return
            with self._lock:
                if self._stop.is_set():
                    return
                self.ready = connected = True
            self.emit("connection", "SIMULATED" if board else f"CONNECTED {self.port}")
            self.send("STATUS")
            while not self._stop.is_set():
                try:
                    epoch, commands = self._commands.get_nowait()
                except queue.Empty:
                    epoch, commands = self._epoch, ()
                for command in commands:
                    if self._stop.is_set() or epoch != self._epoch:
                        break
                    if board:
                        lines = board.execute(command)
                    else:
                        payload = (command + "\n").encode("ascii")
                        if connection.write(payload) != len(payload):
                            raise serial.SerialException("Incomplete command write")
                        lines = []
                    self.emit("tx", command)
                    for line in lines:
                        self.emit("rx", line)
                if board:
                    for line in board.tick():
                        self.emit("rx", line)
                    self._stop.wait(0.01)
                else:
                    pending.extend(connection.read(min(connection.in_waiting or 1, 1024)))
                    while b"\n" in pending:
                        line, _, rest = pending.partition(b"\n")
                        pending = bytearray(rest)
                        self.emit("rx", line.decode("utf-8", errors="replace").strip())
                    if len(pending) > 4096:
                        pending.clear()
                        self.emit("error", "Discarded oversized serial message")
        except Exception as exc:
            self.emit("error", str(exc))
        finally:
            with self._lock:
                self.ready = False
                self._discard_commands()
            if connection:
                try:
                    if connected:
                        # STOP returns the egg controller home; it is not a hardware E-stop.
                        connection.write(b"STOP\n" if self.role == "egg" else b"RESET\n")
                except Exception as exc:
                    self.emit("error", f"Shutdown command failed: {exc}")
                finally:
                    try:
                        connection.close()
                    except Exception as exc:
                        self.emit("error", f"Port close failed: {exc}")
            self.emit("connection", "DISCONNECTED")


class PrototypeRig:
    """Route controls and prevent two workers from opening the same USB port."""

    def __init__(self, events, **link_options):
        self.links = {role: SerialLink(role, events, **link_options)
                      for role in ("egg", "servo")}

    def connect(self, role, port, simulated=False):
        other = self.links["servo" if role == "egg" else "egg"]
        if not simulated and other.active and not other.simulated:
            if port.strip().casefold() == other.port.casefold():
                raise ValueError("Choose different COM ports for the two ESP32 boards.")
        self.links[role].connect(port, simulated)

    def start(self):
        if not all(link.ready for link in self.links.values()):
            raise ValueError("Connect both controllers before starting the conveyor.")
        if len({link.simulated for link in self.links.values()}) != 1:
            raise ValueError("Use hardware for both boards or simulation for both boards.")
        self.links["egg"].send("START")

    def stop(self):
        # Attempt both independently, even if one port has failed.
        failures = []
        for role, command in (("egg", "STOP"), ("servo", "RESET")):
            try:
                self.links[role].send(command, priority=True)
            except ValueError as exc:
                failures.append(str(exc))
        if failures:
            raise ValueError(" ".join(failures))

    def close(self):
        for link in self.links.values():
            link.disconnect()
