"""One owned camera snapshot and its prediction, published together to the UI."""
from copy import deepcopy
from dataclasses import dataclass

from .camera import CameraFrame


@dataclass(frozen=True)
class CaptureView:
    frame: CameraFrame
    result: dict

    @classmethod
    def create(cls, frame, result):
        # Camera snapshots already own their pixels. Never copy them on a Tk tick.
        return cls(frame, deepcopy(result))

    def identity(self):
        return {"sequence": self.frame.sequence, "captured_at": self.frame.captured_at,
                "settings_revision": self.frame.settings_revision}
