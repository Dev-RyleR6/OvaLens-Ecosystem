"""
Unified Single-ESP32 Board Controller for OvaLens.
Connects to the single unified ESP32 controlling Stepper, Sorting Gate, IR, and Lamp on 1 COM port.
"""
import time
from serial.tools import list_ports
import serial
from .dual_board import BoardLink

ROLE = "UNIFIED"
EXPECTED_VERSION = "UNIFIED_V3:PROTOCOL=3"
SerialException = getattr(serial, "SerialException", OSError)


def discover_unified_board(ports=None, serial_factory=None, timeout=4, cancel=None, preferred=None):
    """Scan and discover the single unified OvaLens ESP32 controller."""
    factory = serial_factory or getattr(serial, "Serial", None)
    if factory is None:
        raise RuntimeError("PySerial unavailable; install pyserial")

    candidates = list(ports) if ports is not None else list(preferred or ("COM5", "COM7", "COM9", "COM3", "COM4")) + [p.device for p in list_ports.comports()]
    unique_ports = {}
    for port in candidates:
        if port:
            unique_ports.setdefault(port.casefold(), port)

    port_errors = {}
    for port in unique_ports.values():
        if cancel is not None and cancel.is_set():
            raise RuntimeError("Setup stopped. Retry detection when ready.")
        connection = None
        for attempt in range(3):
            try:
                connection = factory(port, 115200, timeout=0.02, write_timeout=0.2)
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
                if attempt < 2 and ("denied" in err_msg.lower() or "busy" in err_msg.lower()):
                    time.sleep(0.3)
                    continue
                port_errors[port] = err_msg
                break

        if connection is None:
            continue

        try:
            deadline = time.monotonic() + timeout
            sent = 0.0
            buffer = bytearray()
            pong, version = None, None
            while time.monotonic() < deadline:
                if cancel is not None and cancel.is_set():
                    raise RuntimeError("Setup stopped. Retry detection when ready.")
                now = time.monotonic()
                if now - sent >= 0.25:
                    for request in (b"PING\n", b"HELLO\n"):
                        connection.write(request)
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
                if (pong == ROLE or version == EXPECTED_VERSION) or (pong == "CONVEYOR"):
                    return port
        except (OSError, SerialException, UnicodeError):
            continue
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    access_errors = [f"{p} ({err})" for p, err in port_errors.items() if "denied" in err.lower()]
    if access_errors:
        raise RuntimeError(f"Port locked: {', '.join(access_errors)}. Close other apps.")
    raise RuntimeError(f"Unified OvaLens ESP32 not detected. Check USB connection on {preferred or 'COM5'}.")


class UnifiedBoardController:
    """Single-board controller multiplexing conveyor, egg/servo, and light over 1 serial port."""

    def __init__(self, port, serial_factory=None):
        if not port:
            raise ValueError("Select the serial port for the unified ESP32 controller")
        self.port = port
        self.failure = ""
        # The single link to the unified ESP32
        self.link = BoardLink(ROLE, port, self._failure, serial_factory, protocol=3)

        # Proxies so existing ThreeBoardCycle and EdgeStation logic work without modification
        self.conveyor = self.link
        self.servo = self.link
        self.egg = self.link
        self.light = self.link
        self.links = (self.link,)

    def _failure(self, reason):
        if not self.failure:
            self.failure = reason
        self.halt()

    def start(self):
        self.link.start()

    def halt(self):
        self.link.halt()

    def stop(self):
        self.halt()
        self.link.stop()

    def require_ready(self):
        if self.failure:
            raise RuntimeError(self.failure)
        state = self.link.snapshot()
        if not state.connected or not state.identified or state.error or not self.link._status_complete:
            raise RuntimeError("Unified ESP32 controller is not ready")
        if state.telemetry.get("FAULT") != "NONE" or state.telemetry.get("BUSY") != "0":
            raise RuntimeError("Unified controller requires idle fault acknowledgement")
        if state.telemetry.get("REFERENCE_VALID") != "1":
            raise RuntimeError("Conveyor needs an inspected software reference")
        if state.telemetry.get("SENSOR") != "0":
            raise RuntimeError("Clear the chamber IR beam before starting a batch")
        if state.telemetry.get("LIGHT") != "0":
            raise RuntimeError("Turn off the candling lamp before starting")

