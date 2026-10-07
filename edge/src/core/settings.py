"""Validated local defaults. Loading settings never authorizes motion."""
from dataclasses import asdict, dataclass, field
import json
import math
import os
from pathlib import Path
import tempfile


@dataclass
class CameraSettings:
    index: int = 0
    identity: str = ""
    width: int = 1280
    height: int = 720
    fps: int = 30
    # None means leave the driver's current value unchanged.
    exposure: float | None = None
    gain: float | None = None
    focus: float | None = None
    white_balance: float | None = None
    auto_exposure: float | None = None
    autofocus: float | None = None
    auto_white_balance: float | None = None


@dataclass
class DetectionSettings:
    confidence: float = .25
    iou: float = .45
    sort_confidence: float = .85


@dataclass
class CalibrationSettings:
    holder_steps: int = 1000
    sorter_steps: int = 3000
    gate_clearance_steps: int = 100
    direction: int = 1
    speed_us: int = 1000
    ir_offset_steps: int = 0
    position_tolerance_steps: int = 5
    settle_ms: int = 150
    passage_ms: int = 500
    neutral_angle: int = 90
    fertile_angle: int = 60
    infertile_angle: int = 120
    # Deliberately not persisted as authorization. Each connection needs validation.


@dataclass
class EdgeSettings:
    version: int = 1
    conveyor_port: str = ""
    servo_port: str = ""
    camera: CameraSettings = field(default_factory=CameraSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    calibration: CalibrationSettings = field(default_factory=CalibrationSettings)

    def validate(self):
        def integer(value, lo, hi, label):
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError(f"{label} must be a whole number between {lo} and {hi}")
        integer(self.version, 1, 1, "Settings version")
        if not isinstance(self.conveyor_port, str) or not isinstance(self.servo_port, str):
            raise ValueError("Serial ports must be text")
        if self.conveyor_port and self.conveyor_port == self.servo_port:
            raise ValueError("Select separate serial ports for the two boards")
        c, d, k = self.camera, self.detection, self.calibration
        integer(c.index, 0, 99, "Camera index")
        integer(c.width, 160, 7680, "Width")
        integer(c.height, 120, 4320, "Height")
        integer(c.fps, 1, 120, "FPS")
        if not isinstance(c.identity, str):
            raise ValueError("Camera identity must be text")
        for name in ("exposure", "gain", "focus", "white_balance", "auto_exposure", "autofocus", "auto_white_balance"):
            value = getattr(c, name)
            if value is not None and (type(value) not in (float, int) or not math.isfinite(value)):
                raise ValueError(f"{name} must be finite or blank")
        for name, lo in (("confidence", .01), ("iou", .01), ("sort_confidence", .75)):
            value = getattr(d, name)
            if type(value) not in (float, int) or not math.isfinite(value) or not lo <= value <= .99:
                raise ValueError(f"{name} must be between {lo} and 0.99")
        integer(k.holder_steps, 10, 100000, "Holder spacing")
        integer(k.sorter_steps, 1, 1000000, "Sorter distance")
        integer(k.gate_clearance_steps, 1, k.holder_steps // 2 - 1, "Gate clearance")
        if k.sorter_steps <= k.gate_clearance_steps:
            raise ValueError("Sorter must be beyond the gate approach clearance")
        integer(k.direction, -1, 1, "Direction")
        if k.direction == 0:
            raise ValueError("Direction must be -1 or 1")
        integer(k.speed_us, 200, 5000, "STEP half-period")
        integer(k.ir_offset_steps, 0, k.holder_steps - 1, "IR offset")
        integer(k.position_tolerance_steps, 0, k.gate_clearance_steps - 1, "Position tolerance")
        integer(k.settle_ms, 0, 10000, "Settling time")
        integer(k.passage_ms, 0, 10000, "Passage time")
        for name in ("neutral_angle", "fertile_angle", "infertile_angle"):
            integer(getattr(k, name), 0, 180, name)
        # Next egg must not arrive inside the mandatory optical lockout.
        if k.holder_steps * 2 * k.speed_us < 600000:
            raise ValueError("Holder travel must exceed the 600 ms IR lockout")
        return self

    def snapshot(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        for key, kind in (("camera", CameraSettings), ("detection", DetectionSettings), ("calibration", CalibrationSettings)):
            values[key] = kind(**values.get(key, {}))
        return cls(**values).validate()


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path or Path(__file__).resolve().parents[2] / "db" / "edge_settings.json")

    def load(self):
        if not self.path.exists():
            return EdgeSettings()
        try:
            return EdgeSettings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (ValueError, TypeError, OSError) as exc:
            raise ValueError(f"Saved settings could not be loaded: {exc}") from exc

    def save(self, settings):
        settings.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(settings.snapshot(), stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
