"""Disabled compatibility shell for the retired optical-sensor controller.

The two-board spaced-holder rig requires a validated position controller.
This shell must never send motion commands.
"""

import time
import queue
import threading
from typing import Callable, Optional, Dict, Any


class ChamberState:
    STANDBY        = "STANDBY"
    MOTOR_ADVANCE  = "MOTOR_ADVANCE"    # Belt running, waiting for egg
    STABILIZING    = "STABILIZING"      # Belt stopped, light dimmed, settling
    AI_SCAN        = "AI_SCAN"          # Inference in progress
    DISPLAYING     = "DISPLAYING"       # Result shown for operator confirmation
    ACTUATING      = "ACTUATING"        # Servo scheduled / MANUAL_REVIEW flagged
    ADVANCE_NEXT   = "ADVANCE_NEXT"     # Advancing to next egg
    COMPLETE       = "COMPLETE"         # All target eggs processed
    EMERGENCY_STOP = "EMERGENCY_STOP"   # Jam detected (30s timeout)


class ChamberController:
    """Retain callbacks and cancellation while legacy sorting is disabled."""

    def __init__(
        self,
        iot,
        camera,
        inference_queue: queue.Queue,
        result_queue: queue.Queue,
        stabilize_ms: int = 150,
        display_result_ms: int = 1200,
        max_scan_wait_ms: int = 600,
        conf_threshold: float = 0.75,
        jam_timeout_s: float = 30.0,
    ):
        self.iot = iot
        self.camera = camera
        self.inference_queue = inference_queue
        self.result_queue = result_queue
        self.stabilize_ms = stabilize_ms
        self.display_result_ms = display_result_ms   # How long result stays on screen
        self.max_scan_wait_ms = max_scan_wait_ms
        self.conf_threshold = conf_threshold
        self.jam_timeout_s = jam_timeout_s

        self._stop_event = threading.Event()
        self._egg_detected_event = threading.Event()
        self._state: str = ChamberState.STANDBY

        # Callbacks (all called via app.after() for thread safety)
        self.on_state_change: Optional[Callable[[str, int, int], None]] = None
        self.on_scan_result: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_batch_complete: Optional[Callable[[int], None]] = None
        self.on_jam_detected: Optional[Callable[[], None]] = None

    # ─── Public API ───────────────────────────────────────────────────────────

    def notify_egg_detected(self) -> None:
        """Called by ESP32SerialDriver when EVENT:EGG_DETECTED is received."""
        self._egg_detected_event.set()

    def run(self, total_target, conveyor_dist_cm, conveyor_speed_cm_s,
            servo_pulse_ms, scan_light_brightness=200, idle_light_brightness=255):
        """Legacy flow is disabled: it cannot prove sensorless holder identity."""
        raise RuntimeError("Legacy sensor-driven sorting is disabled. "
                           "Use a validated dual-board position controller.")

    def stop(self):
        self._stop_event.set()
        self._egg_detected_event.set()
        # The legacy driver is not permitted to issue motor commands for this rig.

    @property
    def state(self) -> str:
        return self._state

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _emit(self, state: str, current: int, total: int) -> None:
        self._state = state
        if self.on_state_change:
            self.on_state_change(state, current, total)
