"""Session-only station readiness. Passive checks never open serial ports."""
from dataclasses import dataclass
import json
import threading


@dataclass(frozen=True)
class ReadinessCheck:
    key: str
    label: str
    state: str
    detail: str


class StationReadiness:
    def __init__(self, station):
        self.station = station
        self._lock = threading.RLock()
        self._software = {}
        self._prepared = None
        self.reason = "Confirm an empty conveyor, then Prepare station."

    def invalidate(self, reason):
        with self._lock:
            self._prepared = None
            self.reason = reason
            self.station.calibrated = False

    def _fingerprint(self):
        s = self.station
        return (json.dumps(s.settings.snapshot(), sort_keys=True), id(s.boards),
                tuple(id(link) for link in s.board_links()),
                getattr(s.camera, "settings_revision", 0), getattr(s.camera, "identity", ""),
                id(s.inference.engine),
                id(getattr(s.camera, "_thread", None)),
                tuple(tuple(link.snapshot().telemetry.get(key) for key in ("POSITION", "EGG_SEQ", "ANGLE", "PAUSED"))
                      for link in s.board_links()))

    def _controllers(self):
        s = self.station
        s.boards.require_ready()
        if s.settings.rig_profile == "three_v3":
            egg = s.boards.egg.snapshot().telemetry
            conveyor = s.boards.conveyor.snapshot().telemetry
            if egg.get("PAUSED") != "1" or conveyor.get("PAUSED") != "1":
                raise RuntimeError("Conveyor pause is not confirmed. Inspect and prepare again.")
            if egg.get("ANGLE") != str(s.settings.calibration.neutral_angle):
                raise RuntimeError("Sorting gate did not confirm neutral. Inspect and prepare again.")

    def _camera(self):
        camera = self.station.camera
        if camera.is_mock_mode or camera.last_error or camera.snapshot(copy=False) is None:
            raise RuntimeError(camera.last_error or "Camera has no fresh real frame. Use Tools / Retry camera preview.")

    def _model(self):
        engine = self.station.inference.engine
        if not (str(getattr(engine, "engine_type", "")).startswith("ONNX")
                and getattr(engine, "model_contract_verified", False)
                and getattr(engine, "warmup_complete", False)):
            raise RuntimeError("Verified two-class ONNX model and startup warmup are required. Restart after correcting the model.")

    def software_checks(self, progress=lambda message: None):
        """Disk/SQLite work runs on the operation worker, never on Tk."""
        s = self.station
        def settings():
            if s.settings_error:
                raise RuntimeError(s.settings_error + " Open Tools / Settings.")
            s.settings.validate()
        checks = (("settings", "Saved configuration", settings, "Saved settings valid"),
                  ("camera", "Camera", self._camera, "Fresh camera frames available"),
                  ("model", "Classification model", self._model, "ONNX verified; startup warmup complete"),
                  ("storage", "Local scan storage", s.db.check_readiness, "SQLite WAL and image storage writable"))
        for key, label, work, detail in checks:
            progress("Checking " + label.lower())
            try:
                work()
                result = ReadinessCheck(key, label, "Ready", detail)
            except Exception as exc:
                result = ReadinessCheck(key, label, "Needs attention", str(exc))
            with self._lock:
                self._software[key] = result
        error = next((r.detail for r in self._software.values()
                      if r.key != "camera" and r.state == "Needs attention"), None)
        if error:
            self.invalidate(error)
        return self.rows()

    def check_batch(self, batch_id, target):
        from .batches import validate_batch_record
        record = self.station.db.get_local_batch(batch_id)
        if not record:
            raise RuntimeError("Complete this batch in Batch setup before sorting.")
        validate_batch_record(record)
        if record.get("sync_blocked"):
            raise RuntimeError("Batch conflicts with backend details. Ask a manager to resolve it in Batch setup.")
        if target > record["initial_egg_count"]:
            raise RuntimeError("Run target exceeds the original batch inventory.")

    def prepare(self, inspected, cancel, progress=lambda message: None, batch_id=None, target=None):
        s = self.station
        s.require_idle()
        self.invalidate("Preparing station. Keep the conveyor empty.")
        try:
            if not inspected:
                raise RuntimeError("Confirm the conveyor is empty, aligned and the gate checked.")
            s._check_setup_cancel(cancel)
            if batch_id is not None:
                self.check_batch(batch_id, target)
            # Camera settings can discard transient frames; preparation waits for freshness.
            self.software_checks(progress)
            for key in ("settings", "model", "storage"):
                result = self._software[key]
                if result.state != "Ready":
                    raise RuntimeError(result.detail)
            s._check_setup_cancel(cancel)
            s.prepare_for_sorting(True, cancel, progress)
            self._camera()
            self._model()
            self._controllers()
            s._check_setup_cancel(cancel)
            s._check_setup_cancel(s._setup_cancel)
            with self._lock:
                self._prepared = self._fingerprint()
                self.reason = "Station ready. Press Start sorting when ready to feed eggs."
            return self.rows()
        except Exception as exc:
            self.invalidate(str(exc))
            s.halt()
            raise

    def require_ready(self):
        s = self.station
        try:
            with self._lock:
                if self._prepared is None:
                    raise RuntimeError(self.reason)
                if not s.calibrated or self._prepared != self._fingerprint():
                    raise RuntimeError("Prepare station again after inspecting the empty conveyor.")
            self._camera()
            self._model()
            self._controllers()
        except Exception as exc:
            self.invalidate(str(exc))
            raise

    @property
    def ready(self):
        try:
            self.require_ready()
            return True
        except Exception:
            return False

    def start(self, batch_id, target, operator, cancel):
        """Final background recheck, with no discovery, homing or preset replay."""
        s = self.station
        try:
            with s._lock:
                s._check_setup_cancel(cancel)
                self.require_ready()
                for link in s.board_links():
                    s._check_setup_cancel(cancel)
                    link.command("STATUS").result(3.5)
                self.require_ready()
                s.db.check_readiness(full=False)
                self.check_batch(batch_id, target)
                self.require_ready()
                s._check_setup_cancel(cancel)
                s._check_setup_cancel(s._setup_cancel)
                cycle = s.start_cycle(batch_id, target, operator)
                s._check_setup_cancel(cancel)
                s._check_setup_cancel(s._setup_cancel)
                with self._lock:
                    self._prepared = None
                return cycle
        except Exception as exc:
            self.invalidate(str(exc))
            s.halt()
            raise

    def rows(self):
        with self._lock:
            rows = [self._software.get(key, ReadinessCheck(key, label, "Checking", "Waiting for startup checks"))
                    for key, label in (("settings", "Saved configuration"), ("camera", "Camera"),
                                       ("model", "Classification model"), ("storage", "Local scan storage"))]
        # Camera readiness is live, even after the initial software pass.
        try:
            self._camera()
            rows[1] = ReadinessCheck("camera", "Camera", "Ready", "Fresh real camera frames available")
        except Exception as exc:
            rows[1] = ReadinessCheck("camera", "Camera", "Needs attention", str(exc))
        s = self.station
        for attr, key, label in (("conveyor", "stepper", "Stepper controller"),
                                 ("servo", "gate", "Sorting gate and IR"),
                                 ("light", "light", "Light controller")):
            link = getattr(s.boards, attr, None)
            if link is None:
                rows.append(ReadinessCheck(key, label, "Not checked", "Connects after empty-conveyor confirmation"))
                continue
            state = link.snapshot()
            t = state.telemetry
            error = state.error or ("Disconnected" if not state.connected else "" if state.identified else "Identification incomplete")
            if not error and t.get("FAULT") != "NONE":
                error = t.get("FAULT", "Status incomplete")
            if not error and t.get("BUSY") != "0":
                error = "Controller is busy"
            if not error and key == "stepper" and t.get("REFERENCE_VALID") != "1":
                error = "Inspected position reference required"
            if not error and key == "gate" and t.get("SENSOR", t.get("IR_ACTIVE")) != "0":
                error = "Clear the chamber IR beam"
            if not error and key == "light" and t.get("LIGHT") != "0":
                error = "Turn the candling light off before preparing"
            rows.append(ReadinessCheck(key, label, "Needs attention" if error else "Ready",
                error or "Controller acknowledged; physical operation needs inspection"))
        return tuple(rows)
