"""Application service shared by the operator UI and idle settings UI."""
import threading
import time
import uuid
from .settings import EdgeSettings, SettingsStore
from .sorting_cycle import SortingCycle
from .operator_flow import validate_batch_config
from ..iot.dual_board import DualBoardController
from ..iot.three_board import ThreeBoardController, discover_boards
from .three_board_cycle import ThreeBoardCycle


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
        self._lock = threading.RLock()
        self._setup_cancel = threading.Event()

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
            if (settings.camera.index != self.settings.camera.index or settings.rig_profile != self.settings.rig_profile) and not confirm_camera:
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
                                settings.servo_port != self.settings.servo_port or
                                settings.light_port != self.settings.light_port or
                                settings.rig_profile != self.settings.rig_profile):
                self.boards.stop()
                self.boards = None
            self.settings = settings
            self.camera.initial_settings = settings.camera
            if save:
                self.store.save(settings)
            return report

    def apply_camera_controls(self, camera_settings, save=False):
        """Tune only the current camera; no serial commands or model reconfiguration."""
        with self._lock:
            self.require_idle()
            if self.boards:
                state = self.boards.conveyor.snapshot()
                if not state.connected or not state.identified or state.error or state.telemetry.get("BUSY") != "0":
                    raise RuntimeError("Confirm the conveyor is stopped before camera tuning")
            settings = EdgeSettings.from_dict(self.settings.snapshot())
            settings.camera = camera_settings
            settings.validate()
            if settings.camera.index != self.settings.camera.index:
                raise ValueError("Use station settings to change the camera device")
            self.calibrated = False
            report = self.camera.apply_settings(settings.camera, controls_only=True)
            settings.camera.identity = report["identity"]
            self.settings = settings
            self.camera.initial_settings = settings.camera
            if save:
                self.store.save(settings)
            return report

    def connect(self, cancel=None):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if self.boards:
                self.boards.stop()
            if self.settings.rig_profile == "three_v3":
                self.boards = ThreeBoardController(self.settings.conveyor_port, self.settings.servo_port, self.settings.light_port)
            else:
                self.boards = DualBoardController(self.settings.conveyor_port, self.settings.servo_port)
            self.boards.start()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                self._check_setup_cancel(cancel)
                if self.boards.failure:
                    raise RuntimeError(self.boards.failure)
                if all(link._status_complete and link.snapshot().telemetry.get("BUSY") == "0"
                       for link in self.board_links()):
                    if self.settings.rig_profile == "dual_v2" and self.boards.conveyor.snapshot().telemetry.get("IR_CAPABLE") != "1":
                        raise RuntimeError("Conveyor firmware lacks chamber IR capability; update and bench-test firmware")
                    return "Required boards identified. Inspect rig, then acknowledge faults."
                threading.Event().wait(.02)
            raise RuntimeError("Firmware identification timed out")

    @staticmethod
    def _check_setup_cancel(cancel):
        if cancel is not None and cancel.is_set():
            raise RuntimeError("Setup stopped. Inspect the empty conveyor before trying again.")

    def use_defaults_and_detect(self):
        """Explicit operator action: detect, apply and save; leave faults latched."""
        with self._lock:
            self.require_idle()
            self._setup_cancel.clear()
            self.calibrated = False
            if self.boards:
                self.boards.stop()
                self.boards = None
            try:
                settings = EdgeSettings.three_board()
                ports = discover_boards(cancel=self._setup_cancel,
                    preferred=(self.settings.conveyor_port, self.settings.servo_port,
                               self.settings.light_port, "COM5", "COM7", "COM9"))
                settings.conveyor_port = ports["CONVEYOR"]
                settings.servo_port = ports["EGG_CONTROLLER"]
                settings.light_port = ports["LIGHT_CONTROLLER"]
                self._check_setup_cancel(self._setup_cancel)
                self.apply(settings, confirm_camera=True)
                self._check_setup_cancel(self._setup_cancel)
                self.connect(cancel=self._setup_cancel)
                self._check_setup_cancel(self._setup_cancel)
                self.store.save(self.settings)
                self.settings_error = ""
                return (f"Connected: stepper {settings.conveyor_port}, servo + IR {settings.servo_port}, "
                        f"light {settings.light_port}. Check the camera and clear the conveyor, then Prepare conveyor.")
            except Exception:
                self.calibrated = False
                if self.boards:
                    self.boards.stop()
                    self.boards = None
                raise

    def prepare_for_sorting(self, inspected, cancel, progress=lambda message: None):
        """One explicit inspected action; preserve remembered camera/calibration."""
        with self._lock:
            self.require_idle()
            if not inspected:
                raise RuntimeError("Confirm the conveyor is empty, aligned and the gate checked.")
            self._check_setup_cancel(cancel)
            self._setup_cancel.clear()
            self.calibrated = False
            def check():
                self._check_setup_cancel(cancel)
                self._check_setup_cancel(self._setup_cancel)
            try:
                if self.settings_error:
                    raise RuntimeError(self.settings_error + " Open Tools / Settings to correct it.")
                if self.settings.rig_profile != "three_v3":
                    raise RuntimeError("Use Tools / Settings to prepare the saved two-board profile.")
                check()
                progress("Checking camera and saved settings")
                settings = EdgeSettings.from_dict(self.settings.snapshot())
                self.apply(settings)
                settings = EdgeSettings.from_dict(self.settings.snapshot())
                check()
                # Reuse healthy identified links between batches; discovery may reset boards.
                reusable = self.boards is not None and not self.boards.failure and all(
                    link.snapshot().connected and link.snapshot().identified and not link.snapshot().error
                    for link in self.board_links())
                if not reusable:
                    if self.boards:
                        self.boards.stop()
                        self.boards = None
                    progress("Connecting stepper, sorting gate and light")
                    ports = discover_boards(cancel=cancel, preferred=(settings.conveyor_port,
                        settings.servo_port, settings.light_port, "COM5", "COM7", "COM9"))
                    check()
                    settings.conveyor_port, settings.servo_port, settings.light_port = (
                        ports["CONVEYOR"], ports["EGG_CONTROLLER"], ports["LIGHT_CONTROLLER"])
                    self.settings = settings
                    self.connect(cancel=cancel)
                check()
                progress("Checking the empty conveyor and positioning the gate")
                # Applying camera controls discards transient frames on the camera worker.
                deadline = time.monotonic() + 3
                while self.camera.snapshot() is None:
                    check()
                    if self.camera.last_error or time.monotonic() >= deadline:
                        raise RuntimeError("Camera is not ready. Check camera 0, then retry Start sorting.")
                    cancel.wait(.02)
                self.prepare_empty_conveyor(True, cancel=cancel)
                check()
                self.store.save(self.settings)
                return "Station ready"
            except Exception:
                self.halt()
                raise

    def prepare_empty_conveyor(self, inspected, cancel=None):
        """Combine inspected acknowledgement, home and presets without belt travel."""
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if not inspected:
                raise RuntimeError("Confirm the conveyor is empty, aligned and the gate checked.")
            if self.settings.rig_profile != "three_v3" or not self.boards:
                raise RuntimeError("Use defaults & detect first.")
            if self.camera.is_mock_mode or self.camera.last_error or self.camera.snapshot() is None:
                raise RuntimeError("Check the live camera before preparing the conveyor.")
            if not getattr(self.inference.engine, "model_contract_verified", False):
                raise RuntimeError("The existing ONNX model is unavailable. Check Settings before sorting.")
            if cancel is None:
                self._setup_cancel.clear()
            else:
                self._check_setup_cancel(cancel)
                self._check_setup_cancel(self._setup_cancel)
            try:
                for link in self.board_links():
                    state = link.snapshot()
                    if not state.connected or not state.identified or state.error or state.telemetry.get("BUSY") != "0":
                        raise RuntimeError("A board is unavailable or busy. Use defaults & detect again.")
                if self.boards.egg.snapshot().telemetry.get("SENSOR") != "0":
                    raise RuntimeError("Remove the egg from the IR sensor before preparing.")
                commands = [(link, "ACK_FAULT") for link in self.board_links()]
                commands += [(self.boards.light, "LIGHT_OFF"), (self.boards.egg, "PAUSE"),
                             (self.boards.conveyor, "SETHOME")]
                for link, command in commands:
                    self._check_setup_cancel(cancel)
                    self._check_setup_cancel(self._setup_cancel)
                    link.command(command).result(3.5)
                self.validate_calibration(True, cancel=self._setup_cancel, other_cancel=cancel)
                self._check_setup_cancel(cancel)
                self._check_setup_cancel(self._setup_cancel)
                return "Ready. Click Start sorting when you are ready to feed eggs."
            except Exception:
                self.halt()
                raise

    def board_links(self):
        if self.boards is None:
            return ()
        return getattr(self.boards, "links", (self.boards.conveyor, self.boards.servo))

    def discover(self):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if self.boards:
                self.boards.stop()
                self.boards = None
            return discover_boards()

    def command(self, role, text, timeout=5):
        with self._lock:
            self.require_idle()
            if not self.boards:
                raise RuntimeError("Connect and identify the required boards first")
            links = {link.role: link for link in self.board_links()}
            links["SERVO"] = self.boards.servo
            if role not in links:
                raise ValueError("Unknown board role")
            self.calibrated = False
            link = links[role]
            return link.command(text, timeout).result(timeout + .5)

    def validate_calibration(self, inspected, cancel=None, other_cancel=None):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if not inspected or not self.boards:
                raise RuntimeError("Confirm holder alignment and an empty downstream conveyor")
            self.settings.validate()
            self.recovery = self.db.load_machine_state(self.device_id)
            self.boards.require_ready()
            three = self.settings.rig_profile == "three_v3"
            sensor = self.boards.servo.snapshot().telemetry.get("SENSOR") if three else self.boards.conveyor.snapshot().telemetry.get("IR_ACTIVE")
            if sensor != "0":
                raise RuntimeError("Clear the chamber IR beam before validating the next holder")
            k = self.settings.calibration
            commands = [(self.boards.conveyor, f"SPEED:{k.speed_us}"),
                        (self.boards.servo, f"SET_NEUTRAL:{k.neutral_angle}"),
                        (self.boards.servo, f"SET_FERTILE:{k.fertile_angle}"),
                        (self.boards.servo, f"SET_INFERTILE:{k.infertile_angle}"),
                        (self.boards.servo, "RESET")]
            if three:
                commands.extend([(self.boards.light, "LIGHT_OFF"), (self.boards.egg, "ARM")])
            else:
                commands.insert(1, (self.boards.conveyor, f"IR_OFFSET:{k.ir_offset_steps}"))
            for link, text in commands:
                self._check_setup_cancel(cancel)
                self._check_setup_cancel(other_cancel)
                link.command(text).result(3.5)
            self._check_setup_cancel(cancel)
            self._check_setup_cancel(other_cancel)
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
            if not getattr(self.inference.engine, "model_contract_verified", False):
                raise RuntimeError("Verify ONNX dimensions and two-class metadata before sorting")
            self.boards.require_ready()
            kind = ThreeBoardCycle if self.settings.rig_profile == "three_v3" else SortingCycle
            self.cycle = kind(self.boards, self.camera, self.inference, self.db, self.settings,
                self.device_id, str(uuid.uuid4()), batch_id, target, operator)
            self.calibrated = False  # Every batch starts from an inspected reference.
            self.cycle.start()
            return self.cycle

    def halt(self):
        self._setup_cancel.set()
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
