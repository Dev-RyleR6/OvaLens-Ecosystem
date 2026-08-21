"""
Non-blocking PySerial Driver for ESP32 Conveyor Actuator
Handles optical interrupt events, motor stepping/pauses, and delayed servo kick commands (Δt = D/v).
"""

import time
import threading
from typing import Optional, Callable
import serial
import serial.tools.list_ports


class ESP32SerialDriver:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.ser: Optional[serial.Serial] = None
        self._is_running = False
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._on_egg_detected_callback: Optional[Callable[[], None]] = None
        self._is_mock_mode = False
        self._last_heartbeat = 0.0

    def start(self, on_egg_detected: Optional[Callable[[], None]] = None):
        """Connect to serial port and start listener thread."""
        self._on_egg_detected_callback = on_egg_detected
        self._connect()
        self._is_running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True, name="OvaLens-SerialThread")
        self._reader_thread.start()

    def _connect(self):
        # Auto-detect ESP32 if port is not specified
        if not self.port:
            available_ports = serial.tools.list_ports.comports()
            for p in available_ports:
                desc = (p.description or "").lower()
                if "ch340" in desc or "cp210" in desc or "usb" in desc or "serial" in desc or "esp32" in desc:
                    self.port = p.device
                    break

        if self.port:
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                self._is_mock_mode = False
                print(f"[SUCCESS] Connected to ESP32 on {self.port} @ {self.baudrate} baud.")
                return
            except Exception as e:
                print(f"[WARN] Could not open Serial port {self.port} ({e}). Entering Mock Serial mode.")

        self._is_mock_mode = True
        print("[WARN] No physical ESP32 detected. Running in Mock Actuator mode.")

    def _read_loop(self):
        """Background thread parsing incoming serial lines."""
        while self._is_running:
            if not self._is_mock_mode and self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            self._handle_incoming_line(line)
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    print(f"[WARN] Serial read error ({e}). Attempting reconnect...")
                    time.sleep(1.0)
                    self._connect()
            else:
                time.sleep(0.05)

    def _handle_incoming_line(self, line: str):
        if line == "EVENT:EGG_DETECTED":
            if self._on_egg_detected_callback:
                self._on_egg_detected_callback()
        elif line.startswith("RESP:PONG"):
            self._last_heartbeat = time.time()
        elif line.startswith("RESP:"):
            pass

    def schedule_ejection(self, delay_ms: int, pulse_ms: int = 250):
        """Schedule a delayed servo/solenoid stroke (Δt = D/v)."""
        cmd = f"CMD:EJECT:{int(delay_ms)}:{int(pulse_ms)}\n"
        self._send_raw(cmd)

    def trigger_ejection_now(self):
        """Trigger immediate manual ejection."""
        self._send_raw("CMD:EJECT_NOW\n")

    def set_conveyor(self, is_running: bool):
        """Start or stop conveyor belt motor."""
        cmd = "CMD:MOTOR:START\n" if is_running else "CMD:MOTOR:STOP\n"
        self._send_raw(cmd)

    def set_candling_light(self, brightness_0_to_255: int):
        """Adjust candling lamp PWM brightness."""
        val = max(0, min(255, brightness_0_to_255))
        self._send_raw(f"CMD:LIGHT:{val}\n")

    def ping(self):
        """Send heartbeat ping."""
        self._send_raw("CMD:PING\n")

    def _send_raw(self, cmd: str):
        if not self._is_mock_mode and self.ser and self.ser.is_open:
            with self._lock:
                try:
                    self.ser.write(cmd.encode("utf-8"))
                    self.ser.flush()
                except Exception as e:
                    print(f"[ERROR] Serial write failure ({e})")
        else:
            # Mock mode pass-through
            pass

    @property
    def is_connected(self) -> bool:
        return (not self._is_mock_mode) and (self.ser is not None) and self.ser.is_open

    def stop(self):
        """Close serial connection and terminate worker thread."""
        self._is_running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
