"""Application service shared by the operator UI and idle settings UI."""
import threading
import time
import uuid
from .settings import EdgeSettings, SettingsStore
from .sorting_cycle import SortingCycle
from .operator_flow import validate_batch_config
from ..iot.dual_board import BoardLink, DualBoardController
from ..iot.three_board import ThreeBoardController, discover_boards
from .three_board_cycle import ThreeBoardCycle
from .readiness import StationReadiness


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
        self._camera_alignment_boards = None
        self._manual_light_link = None
        self._manual_light_cancel = threading.Event()
        self._manual_light_cancel.set()
        self._manual_light_interval = 5.0
        self.readiness = StationReadiness(self)

    @property
    def light_link(self):
        return getattr(self.boards, "light", None) if self.boards else self._manual_light_link

    def set_manual_light(self, enabled, cancel=None):
        """Idle lamp-only action; connecting it never opens the motor/servo ports."""
        if type(enabled) is not bool:
            raise ValueError("Choose light on or off")
        self.require_idle()
        self._manual_light_cancel.set()
        cancel = cancel if cancel is not None else threading.Event()
        self._manual_light_cancel = cancel
        with self._lock:
            self.require_idle()
            self._check_setup_cancel(cancel)
            if self.settings.rig_profile != "three_v3":
                raise RuntimeError("Manual light requires the three-board v3 light controller")
            if self.boards and self.boards.conveyor.snapshot().telemetry.get("BUSY") != "0":
                raise RuntimeError("Stop the conveyor before switching the light")
            link = self.light_link
            try:
                if link is not None and link is self._manual_light_link:
                    state = link.snapshot()
                    if not state.connected or state.error:
                        link.stop()
                        self._manual_light_link = link = None
                if link is None:
                    link = self._manual_light_link = BoardLink("LIGHT_CONTROLLER",
                        self.settings.light_port or "COM9", lambda reason: self._manual_light_cancel.set(), protocol=3)
                    link.start()
                    deadline = time.monotonic() + 5
                    while not link._status_complete:
                        self._check_setup_cancel(cancel)
                        state = link.snapshot()
                        if state.error or time.monotonic() >= deadline:
                            raise RuntimeError(state.error or "Light controller identification timed out")
                        cancel.wait(.02)
                self._check_setup_cancel(cancel)
                state = link.snapshot()
                if not state.connected or not state.identified or state.error:
                    raise RuntimeError(state.error or "Light controller is disconnected")
                if enabled:
                    fault = state.telemetry.get("FAULT")
                    if fault not in {"NONE", "STARTUP_ACK_REQUIRED", "EMERGENCY_STOP", "LIGHT_AUTO_OFF_TIMEOUT"}:
                        raise RuntimeError("Inspect the light controller fault before turning it on")
                    if fault != "NONE":
                        link.command("ACK_FAULT").result(3.5)
                self._check_setup_cancel(cancel)
                reply = link.command("LIGHT_ON" if enabled else "LIGHT_OFF").result(3.5)
                self._check_setup_cancel(cancel)
                if reply.get("LIGHT") != ("1" if enabled else "0"):
                    raise RuntimeError("Light controller did not confirm the requested state")
                if enabled:
                    threading.Thread(target=self._renew_manual_light, args=(link, cancel),
                        daemon=True, name="OvaLens-ManualLight").start()
                else:
                    cancel.set()
                return "Candling light on." if enabled else "Candling light off."
            except Exception:
                cancel.set()
                if link:
                    link.halt()
                if link and link is self._manual_light_link:
                    link.stop()
                    self._manual_light_link = None
                raise

    def _renew_manual_light(self, link, cancel):
        # Keep the firmware's 15s watchdog intact if the app or USB link fails.
        while not cancel.wait(self._manual_light_interval):
            with self._lock:
                if cancel.is_set() or self.active or link is not self.light_link:
                    return
                try:
                    state = link.snapshot()
                    if state.error or state.telemetry.get("FAULT") != "NONE":
                        raise RuntimeError("Light controller is unavailable")
                    if link.command("LIGHT_ON").result(3.5).get("LIGHT") != "1":
                        raise RuntimeError("Light controller did not confirm ON")
                    if cancel.is_set():
                        link.halt()
                except Exception:
                    cancel.set()
                    link.halt()
                    return

    def release_manual_light(self):
        """Release COM ownership before discovery/preparation or a new batch."""
        with self._lock:
            owned = not self._manual_light_cancel.is_set()
            self._manual_light_cancel.set()
            if self._manual_light_link:
                self._manual_light_link.stop()
                self._manual_light_link = None
            elif owned and self.light_link:
                link = self.light_link
                if link.command("LIGHT_OFF").result(3.5).get("LIGHT") != "0":
                    link.halt()
                    raise RuntimeError("Light controller did not confirm OFF")

    @property
    def active(self):
        return self.cycle is not None and self.cycle.active

    def require_idle(self):
        if self.active:
            raise RuntimeError("Stop sorting before changing station settings")

    def apply(self, settings, save=False, confirm_camera=False):
        with self._lock:
            self.require_idle()
            self.release_manual_light()
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
            self.settings_error = ""
            return report

    def apply_camera_controls(self, camera_settings, save=False, live_preview=False):
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
            options = {"controls_only": True}
            if live_preview:
                options["live_preview"] = True
            report = self.camera.apply_settings(settings.camera, **options)
            settings.camera.identity = report["identity"]
            self.settings = settings
            self.camera.initial_settings = settings.camera
            if save:
                self.store.save(settings)
            return report

    def connect(self, cancel=None):
        with self._lock:
            self.require_idle()
            self.release_manual_light()
            self._camera_alignment_boards = None
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
            self.release_manual_light()
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
            self.release_manual_light()
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
            self.release_manual_light()
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
            self.release_manual_light()
            links = {link.role: link for link in self.board_links()}
            links["SERVO"] = self.boards.servo
            if role not in links:
                raise ValueError("Unknown board role")
            self.calibrated = False
            link = links[role]
            return link.command(text, timeout).result(timeout + .5)

    def prepare_camera_alignment(self, inspected, cancel=None):
        """Explicit idle alignment setup: connect, hold, slow jog speed and lamp."""
        with self._lock:
            self.require_idle()
            if not inspected:
                raise RuntimeError("Check the cradle path is clear before connecting for alignment")
            if self.settings.rig_profile != "three_v3":
                raise RuntimeError("Camera alignment controls require the three-board v3 rig")
            if self.settings_error:
                raise RuntimeError(self.settings_error + " Correct saved settings before alignment.")
            self._check_setup_cancel(cancel)
            self._setup_cancel.clear()
            def check():
                self._check_setup_cancel(cancel)
                self._check_setup_cancel(self._setup_cancel)
            self.calibrated = False
            self._camera_alignment_boards = None
            try:
                reusable = self.boards is not None and not self.boards.failure and all(
                    link.snapshot().connected and link.snapshot().identified and not link.snapshot().error
                    for link in self.board_links())
                if not reusable:
                    self.connect(cancel=cancel or self._setup_cancel)
                for link in self.board_links():
                    check()
                    state = link.snapshot()
                    if state.telemetry.get("BUSY") != "0":
                        raise RuntimeError("Wait for all boards to stop before alignment")
                    fault = state.telemetry.get("FAULT")
                    if fault not in {"NONE", "STARTUP_ACK_REQUIRED", "EMERGENCY_STOP"}:
                        raise RuntimeError("Inspect board faults in Tools / Settings before alignment")
                    if fault != "NONE":
                        link.command("ACK_FAULT").result(3.5)
                for link, text in ((self.boards.egg, "PAUSE"), (self.boards.conveyor, "SPEED:5000"),
                                   (self.boards.light, "LIGHT_ON")):
                    check()
                    link.command(text).result(3.5)
                check()
                self._camera_alignment_boards = self.boards
                check()
                return "Alignment ready. Lamp on; conveyor held. Choose a short jog."
            except Exception:
                self.halt()
                raise

    def jog_camera_cradle(self, steps, cancel=None):
        """One bounded manual move; no home reset, classification or automatic retry."""
        if type(steps) is not int or not 1 <= abs(steps) <= 1000:
            raise ValueError("Choose 1 to 1000 steps per jog")
        with self._lock:
            self.require_idle()
            if self.boards is None or self._camera_alignment_boards is not self.boards:
                raise RuntimeError("Connect for alignment before jogging the cradle")
            self.calibrated = False
            def check():
                self._check_setup_cancel(cancel)
                self._check_setup_cancel(self._setup_cancel)
            try:
                check()
                for link in self.board_links():
                    state = link.snapshot()
                    if (not state.connected or not state.identified or state.error
                            or state.telemetry.get("FAULT") != "NONE" or state.telemetry.get("BUSY") != "0"):
                        raise RuntimeError("Alignment requires healthy, stopped boards")
                conveyor = self.boards.conveyor
                before = int(conveyor.command("STATUS").result(3.5)["POSITION"])
                check()
                self.boards.egg.command("RESUME").result(3.5)
                check()
                state = conveyor.command("STATUS").result(3.5)
                if state.get("PAUSED") != "0" or state.get("BUSY") != "0" or state.get("FAULT") != "NONE":
                    raise RuntimeError("Hardware pause is still active; inspect the pause wiring")
                check()
                timeout = 3 + abs(steps) * .01  # 5000 us half-period: 10ms per step.
                result = conveyor.command(f"JOG:{steps}", timeout).result(timeout + .5)
                check()
                actual = int(result["POSITION"]) - before
                if (result.get("BUSY") != "0" or result.get("FAULT") != "NONE"
                        or not 0 <= actual * (1 if steps > 0 else -1) <= abs(steps)):
                    raise RuntimeError("Unexpected jog completion; inspect the cradle position")
                self.boards.egg.command("PAUSE").result(3.5)
                check()
                note = " (sensor held the move early)" if actual != steps else ""
                return f"Cradle moved {actual} steps; position {result['POSITION']}. Conveyor held{note}."
            except Exception:
                self.halt()
                raise

    def finish_camera_alignment(self):
        with self._lock:
            if self._camera_alignment_boards is None:
                return
            self._manual_light_cancel.set()
            self._camera_alignment_boards = None
            self.calibrated = False
            try:
                self._check_setup_cancel(self._setup_cancel)
                self.boards.egg.command("PAUSE").result(3.5)
                self._check_setup_cancel(self._setup_cancel)
                self.boards.light.command("LIGHT_OFF").result(3.5)
            except Exception:
                self.halt()
                raise

    def validate_calibration(self, inspected, cancel=None, other_cancel=None):
        with self._lock:
            self.require_idle()
            self.calibrated = False
            if not inspected or not self.boards:
                raise RuntimeError("Confirm holder alignment and an empty downstream conveyor")
            self.release_manual_light()
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
            self.release_manual_light()
            if self._camera_alignment_boards is not None:
                raise RuntimeError("Finish camera alignment before sorting")
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
        self._manual_light_cancel.set()
        if self._manual_light_link:
            self._manual_light_link.halt()
        self._setup_cancel.set()
        self._camera_alignment_boards = None
        self.calibrated = False
        if self.cycle:
            self.cycle.stop()
        if self.boards:
            self.boards.halt()

    def stop(self):
        self.halt()
        if self._manual_light_link:
            self._manual_light_link.stop()
            self._manual_light_link = None
        if self.cycle and self.cycle._thread:
            self.cycle._thread.join(timeout=3)
        if self.boards:
            self.boards.stop()
