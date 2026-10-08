"""Three-board v3 transport. Discovery never acknowledges faults or moves hardware."""
import time
from serial.tools import list_ports
import serial
from .dual_board import BoardLink

ROLES = ("CONVEYOR", "EGG_CONTROLLER", "LIGHT_CONTROLLER")


def discover_boards(ports=None, serial_factory=None, timeout=4):
    factory = serial_factory or getattr(serial, "Serial", None)
    if factory is None:
        raise RuntimeError("PySerial unavailable; install pyserial, not the unrelated serial package")
    found = {}
    candidates = ports if ports is not None else [p.device for p in list_ports.comports()]
    for port in candidates:
        connection = None
        try:
            connection = factory(port, 115200, timeout=.02, write_timeout=.2)
            deadline, sent = time.monotonic() + timeout, 0.0
            buffer = bytearray()
            pong, version = None, None
            while time.monotonic() < deadline:
                now = time.monotonic()
                if now - sent >= .25:
                    for request in (b"PING\n", b"HELLO\n"):
                        if connection.write(request) != len(request):
                            raise RuntimeError("Incomplete discovery write")
                    sent = now
                for byte in connection.read(256):
                    if byte == 10:
                        line = buffer.decode("ascii", errors="strict").strip()
                        buffer.clear()
                        if line.startswith("PONG:"):
                            pong = line[5:]
                        if line.startswith("READY:"):
                            version = line[6:]
                    elif byte != 13:
                        buffer.append(byte)
                        if len(buffer) > 256:
                            raise RuntimeError("Oversized discovery reply")
                if pong in ROLES and version == f"{pong}_V3:PROTOCOL=3":
                    if pong in found:
                        raise ValueError(f"Duplicate {pong} boards: {found[pong]} and {port}")
                    found[pong] = port
                    break
        except (OSError, serial.SerialException, UnicodeError):
            continue
        finally:
            if connection is not None:
                connection.close()
    missing = set(ROLES) - set(found)
    if missing:
        raise RuntimeError("Missing v3 boards: " + ", ".join(sorted(missing)))
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
