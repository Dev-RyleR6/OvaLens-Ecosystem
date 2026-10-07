"""Application service shared by the operator UI and idle settings UI."""
import threading
import time
import uuid
from .settings import EdgeSettings, SettingsStore
from .sorting_cycle import SortingCycle
from .operator_flow import validate_batch_config
from ..iot.dual_board import DualBoardController


class EdgeStation:
    def __init__(self, camera, inference, db, device_id, store=None):
        self.camera, self.inference, self.db, self.device_id = camera, inference, db, device_id
        self.store = store or SettingsStore()
        self.settings_error = ""
        try:
            self.settings = self.store.load()
        except ValueError as exc:
            self.settings_error = str(exc)
            self.settings = EdgeSettings()
        self.boards = None
        self.cycle = None
        self.calibrated = False
        self.recovery = db.load_machine_state(device_id)
        self._lock = threading.Lock()

    @property
    def active(self):
        return self.cycle is not None and self.cycle.active

    def require_idle(self):
        if self.active:
            raise RuntimeError("Stop sorting before changing station settings")

    def apply(self, settings, save=False, confirm_camera=False):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            settings = EdgeSettings.from_dict(settings.snapshot())
            if settings.camera.index != self.settings.camera.index and not confirm_camera:
                raise ValueError("Confirm the selected camera before changing devices")
            if confirm_camera:
                settings.camera.identity = ""
            report = self.camera.apply_settings(settings.camera)
            settings.camera.identity = report["identity"]
            def configure():
                self.inference.engine.conf_threshold = settings.detection.confidence
                self.inference.engine.iou_threshold = settings.detection.iou
                return {}
            self.inference.predict(configure, capture=True, timeout=3)
            # Any applied configuration requires fresh physical validation.
            self.calibrated = False
            if self.boards and (settings.conveyor_port != self.settings.conveyor_port or
                                settings.servo_port != self.settings.servo_port):
                self.boards.stop()
                self.boards = None
            self.settings = settings
            self.camera.initial_settings = settings.camera
            if save:
                self.store.save(settings)
            return report

    def connect(self):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if self.boards:
                self.boards.stop()
            self.boards = DualBoardController(self.settings.conveyor_port, self.settings.servo_port)
            self.boards.start()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if self.boards.failure:
                    raise RuntimeError(self.boards.failure)
                if all(link._status_complete and link.snapshot().telemetry.get("BUSY") == "0"
                       for link in (self.boards.conveyor, self.boards.servo)):
                    if self.boards.conveyor.snapshot().telemetry.get("IR_CAPABLE") != "1":
                        raise RuntimeError("Conveyor firmware lacks chamber IR capability; update and bench-test firmware")
                    return "Both v2 boards identified. Inspect rig, then acknowledge faults."
                threading.Event().wait(.02)
            raise RuntimeError("Firmware identification timed out")

    def command(self, role, text, timeout=5):
        with self._lock:
            self.require_idle()
            if not self.boards:
                raise RuntimeError("Connect and identify both boards first")
            if role not in {"CONVEYOR", "SERVO"}:
                raise ValueError("Unknown board role")
            self.calibrated = False
            link = self.boards.conveyor if role == "CONVEYOR" else self.boards.servo
            return link.command(text, timeout).result(timeout + .5)

    def validate_calibration(self, inspected):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if not inspected or not self.boards:
                raise RuntimeError("Confirm holder alignment and an empty downstream conveyor")
            self.settings.validate()
            self.recovery = self.db.load_machine_state(self.device_id)
            self.boards.require_ready()
            if self.boards.conveyor.snapshot().telemetry.get("IR_ACTIVE") != "0":
                raise RuntimeError("Clear the chamber IR beam before validating the next holder")
            k = self.settings.calibration
            commands = [(self.boards.conveyor, f"SPEED:{k.speed_us}"),
                        (self.boards.conveyor, f"IR_OFFSET:{k.ir_offset_steps}"),
                        (self.boards.servo, f"SET_NEUTRAL:{k.neutral_angle}"),
                        (self.boards.servo, f"SET_FERTILE:{k.fertile_angle}"),
                        (self.boards.servo, f"SET_INFERTILE:{k.infertile_angle}"),
                        (self.boards.servo, "RESET")]
            for link, text in commands:
                link.command(text).result(3.5)
            if self.recovery and self.recovery.get("state") not in {"COMPLETE", "CLEARED"}:
                session_id = self.recovery.get("session_id")
                if session_id and self.db.get_session_stats(session_id):
                    self.db.complete_session(session_id)
            self.db.save_machine_state(self.device_id, {"state": "CLEARED",
                "previous_session": (self.recovery or {}).get("session_id"), "operator_inspected": True})
            self.recovery = None
            self.calibrated = True
            return "Calibration loaded and inspected for this connection. No conveyor motion started."

    def start_cycle(self, batch_id, target, operator):
        with self._lock:
            self.require_idle()
            batch_id, operator, target = validate_batch_config(batch_id, operator, target, "DAY_10")
            if not self.calibrated or not self.boards:
                raise RuntimeError("Validate calibration and holder alignment before sorting")
            if not str(self.inference.engine.engine_type).startswith("ONNX"):
                raise RuntimeError("Real ONNX model is required for sorting")
            self.boards.require_ready()
            self.cycle = SortingCycle(self.boards, self.camera, self.inference, self.db, self.settings,
                self.device_id, str(uuid.uuid4()), batch_id, target, operator)
            self.calibrated = False  # Every batch starts from an inspected reference.
            self.cycle.start()
            return self.cycle

    def halt(self):
        self.calibrated = False
        if self.cycle:
            self.cycle.stop()
        if self.boards:
            self.boards.halt()

    def stop(self):
        self.halt()
        if self.cycle and self.cycle._thread:
            self.cycle._thread.join(timeout=3)
        if self.boards:
            self.boards.stop()
