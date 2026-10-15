"""Three-board v3 transport. Discovery never acknowledges faults or moves hardware."""
import time
from serial.tools import list_ports
import serial
from .dual_board import BoardLink

ROLES = ("CONVEYOR", "EGG_CONTROLLER", "LIGHT_CONTROLLER")
SerialException = getattr(serial, "SerialException", OSError)


def discover_boards(ports=None, serial_factory=None, timeout=4, cancel=None, preferred=None):
    factory = serial_factory or getattr(serial, "Serial", None)
    if factory is None:
        raise RuntimeError("PySerial unavailable; install pyserial, not the unrelated serial package")
    found = {}
    port_errors = {}
    automatic = ports is None
    candidates = list(ports) if ports is not None else list(preferred or ("COM5", "COM7", "COM9")) + [p.device for p in list_ports.comports()]
    unique_ports = {}
    for port in candidates:
        if port:
            unique_ports.setdefault(port.casefold(), port)
    for port in unique_ports.values():
        if cancel is not None and cancel.is_set():
            raise RuntimeError("Setup stopped. Retry detection when ready.")
        connection = None
        for attempt in range(3):
            try:
                connection = factory(port, 115200, timeout=.02, write_timeout=.2)
                if hasattr(connection, "dtr"):
                    try:
                        connection.dtr = False
                        connection.rts = False
                    except Exception:
                        pass
                if hasattr(connection, "reset_input_buffer"):
                    try:
                        connection.reset_input_buffer()
                    except Exception:
                        pass
                break
            except Exception as exc:
                err_msg = str(exc)
                if attempt < 2 and ("denied" in err_msg.lower() or "busy" in err_msg.lower() or "permission" in err_msg.lower()):
                    time.sleep(0.3)
                    continue
                port_errors[port] = err_msg
                break
        if connection is None:
            continue
        try:
            deadline, sent = time.monotonic() + timeout, 0.0
            buffer = bytearray()
            pong, version = None, None
            while time.monotonic() < deadline:
                if cancel is not None and cancel.is_set():
                    raise RuntimeError("Setup stopped. Retry detection when ready.")
                now = time.monotonic()
                if now - sent >= .25:
                    for request in (b"PING\n", b"HELLO\n"):
                        if connection.write(request) != len(request):
                            raise RuntimeError("Incomplete discovery write")
                    sent = now
                for byte in connection.read(256):
                    if byte == 10:
                        line = buffer.decode("ascii", errors="ignore").strip()
                        buffer.clear()
                        if line.startswith("PONG:"):
                            pong = line[5:]
                        if line.startswith("READY:"):
                            version = line[6:]
                    elif byte != 13:
                        buffer.append(byte)
                        if len(buffer) > 256:
                            buffer.clear()
                if version and not pong:
                    role_cand = version.partition("_V3")[0]
                    if role_cand in ROLES and version == f"{role_cand}_V3:PROTOCOL=3":
                        pong = role_cand
                if pong in ROLES and version == f"{pong}_V3:PROTOCOL=3":
                    if pong in found:
                        raise ValueError(f"Duplicate {pong} boards: {found[pong]} and {port}")
                    found[pong] = port
                    break
        except (OSError, SerialException, UnicodeError):
            continue
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
        if automatic and len(found) == len(ROLES):
            break
    missing = set(ROLES) - set(found)
    if missing:
        access_errors = [f"{p} (access denied / in use)" for p, err in port_errors.items()
                         if "denied" in err.lower() or "permission" in err.lower()]
        if access_errors:
            raise RuntimeError(f"Missing v3 boards: {', '.join(sorted(missing))}. "
                               f"Port locked: {', '.join(access_errors)}. Close other OvaLens instances or Arduino Serial Monitor.")
        raise RuntimeError("Missing v3 boards: " + ", ".join(sorted(missing))
                           + ". Check USB cables and install the matching firmware/three_board sketches.")
    return found


class ThreeBoardController:
    def __init__(self, conveyor_port, egg_port, light_port, serial_factory=None):
        ports = (conveyor_port, egg_port, light_port)
        if not all(ports) or len({p.casefold() for p in ports}) != 3:
            raise ValueError("Select three different serial ports or discover the v3 boards")
        self.failure = ""
        self.conveyor, self.servo, self.light = [
            BoardLink(role, port, self._failure, serial_factory, protocol=3)
            for role, port in zip(ROLES, ports)]
        self.egg = self.servo
        self.links = (self.conveyor, self.egg, self.light)

    def _failure(self, reason):
        if not self.failure:
            self.failure = reason
        self.halt()

    def start(self):
        for link in self.links:
            link.start()

    def halt(self):
        for link in self.links:
            link.halt()

    def stop(self):
        self.halt()
        for link in self.links:
            link.stop()

    def require_ready(self):
        if self.failure:
            raise RuntimeError(self.failure)
        for link in self.links:
            state = link.snapshot()
            if not state.connected or not state.identified or state.error or not link._status_complete:
                raise RuntimeError(f"{link.role} is not ready")
            if state.telemetry.get("FAULT") != "NONE" or state.telemetry.get("BUSY") != "0":
                raise RuntimeError(f"{link.role} requires idle fault acknowledgement")
        if self.conveyor.snapshot().telemetry.get("REFERENCE_VALID") != "1":
            raise RuntimeError("Conveyor needs an inspected software reference")
        if self.egg.snapshot().telemetry.get("SENSOR") != "0":
            raise RuntimeError("Clear the chamber before starting a batch")
        if self.light.snapshot().telemetry.get("LIGHT") != "0":
            raise RuntimeError("Turn off the candling lamp before starting")
