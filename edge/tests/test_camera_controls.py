"""TASK-NEW-EDGE-CAMERA-PREVIEW-01: camera-only tuning, no physical devices."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import threading
import time

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.camera import CameraGrabber
from src.core.camera_controls import camera_values, exposure_modes, mode_label, NUMERIC_CONTROLS, AUTO_CONTROLS
from src.core.settings import CameraSettings, EdgeSettings, SettingsStore
from src.core.station import EdgeStation


@pytest.mark.parametrize("identity,normalized,expected", [
    ("opencv:0:DSHOW", False, {"On": 1., "Off": 0.}),
    ("opencv:0:V4L2", False, {"On": 3., "Off": 1.}),
    ("opencv:0:V4L2", True, {"On": .75, "Off": .25}),
    ("opencv:0:MSMF", False, {}),
])
def test_auto_exposure_uses_backend_modes(identity, normalized, expected):
    assert exposure_modes(identity, normalized) == expected


def test_control_values_keep_identity_stream_and_saved_custom_mode():
    current = CameraSettings(identity="opencv:0:DSHOW", autofocus=.5, exposure=-6)
    entries = {name: "" for name in NUMERIC_CONTROLS}
    entries.update(brightness="10", sharpness="2")
    modes = {name: "Unchanged" for name in AUTO_CONTROLS}
    modes["autofocus"] = "Saved value"
    result = camera_values(current, entries, modes, exposure_modes(current.identity))
    assert result.identity == current.identity and result.width == 1280 and result.index == 0
    assert result.autofocus == .5 and result.brightness == 10 and result.sharpness == 2
    assert current.exposure == -6 and current.brightness is None
    assert mode_label(.5, {"On": 1., "Off": 0.}) == "Saved value"


@pytest.mark.parametrize("text", ["nan", "inf", "abc"])
def test_bad_numeric_values_never_reach_camera(text):
    entries = {name: "" for name in NUMERIC_CONTROLS}
    entries["focus"] = text
    with pytest.raises(ValueError):
        camera_values(CameraSettings(), entries, {name: "Unchanged" for name in AUTO_CONTROLS}, {})


def test_automatic_modes_clear_inactive_manual_requests():
    entries = {name: "20" for name in NUMERIC_CONTROLS}
    result = camera_values(CameraSettings(), entries, {name: "On" for name in AUTO_CONTROLS}, {"On": 1., "Off": 0.})
    assert result.focus is result.exposure is result.white_balance is None
    assert result.autofocus == result.auto_exposure == result.auto_white_balance == 1
    assert result.gain == 20


def test_camera_only_apply_on_owner_preserves_stream_and_skips_auto_manual_conflict(monkeypatch):
    class Capture:
        def __init__(self):
            self.values, self.calls = {}, []
        def isOpened(self):
            return True
        def getBackendName(self):
            return "DSHOW"
        def set(self, prop, value):
            self.calls.append((prop, value, threading.get_ident()))
            if prop == cv2.CAP_PROP_SHARPNESS:
                return False
            self.values[prop] = value
            return True
        def get(self, prop):
            return self.values.get(prop, 0)
        def read(self):
            time.sleep(.005)
            return True, np.zeros((120, 160, 3), dtype=np.uint8)
        def release(self):
            pass
    capture = Capture()
    monkeypatch.setattr("src.core.camera.cv2.VideoCapture", lambda *args: capture)
    camera = CameraGrabber()
    try:
        camera.apply_settings(CameraSettings())
        capture.calls.clear()
        settings = CameraSettings(autofocus=1, focus=100, auto_exposure=0,
            exposure=-6, brightness=12, sharpness=7)
        report = camera.apply_settings(settings, controls_only=True)
        properties = [p for p, _, _ in capture.calls]
        assert cv2.CAP_PROP_FRAME_WIDTH not in properties and cv2.CAP_PROP_FPS not in properties
        assert cv2.CAP_PROP_FOCUS not in properties
        assert properties.index(cv2.CAP_PROP_AUTO_EXPOSURE) < properties.index(cv2.CAP_PROP_EXPOSURE)
        assert all(owner != threading.get_ident() for _, _, owner in capture.calls)
        assert report["properties"]["brightness"]["status"] == "verified readback"
        assert report["properties"]["sharpness"]["status"] == "rejected / unsupported"
        assert report["properties"]["focus"]["status"] == "inactive while automatic mode is on"
        assert report["exposure_modes"] == {"On": 1., "Off": 0.}
    finally:
        camera.stop()


def test_camera_service_saves_only_camera_values_and_does_not_issue_serial_commands(tmp_path):
    settings = EdgeSettings.three_board()
    settings.calibration.settle_ms = 1900
    store = SettingsStore(tmp_path / "settings.json")
    store.save(settings)
    camera = SimpleNamespace(apply_settings=Mock(return_value={"identity": "opencv:0:DSHOW", "properties": {}}))
    station = EdgeStation(camera, Mock(), Mock(load_machine_state=Mock(return_value=None)), "station", store)
    station.boards = SimpleNamespace(conveyor=SimpleNamespace(snapshot=lambda: SimpleNamespace(
        connected=True, identified=True, error=None, telemetry={"BUSY": "0"})), command=Mock())
    controls = CameraSettings(autofocus=0, focus=80, brightness=10)
    station.apply_camera_controls(controls, save=False)
    assert store.load().camera.focus is None
    station.apply_camera_controls(controls, save=True)
    saved = store.load()
    assert saved.camera.focus == 80 and saved.camera.brightness == 10
    assert saved.calibration.settle_ms == 1900 and saved.conveyor_port == "COM5"
    station.boards.command.assert_not_called()
    station.inference.predict.assert_not_called()
    camera.apply_settings.assert_called_with(controls, controls_only=True)
    assert not station.calibrated


@pytest.mark.parametrize("blocked", ["active", "moving", "device"])
def test_camera_service_rejects_operation_conflicts_before_hardware(tmp_path, blocked):
    camera = SimpleNamespace(apply_settings=Mock())
    station = EdgeStation(camera, Mock(), Mock(load_machine_state=Mock(return_value=None)),
                          "station", SettingsStore(tmp_path / "defaults.json"))
    if blocked == "active":
        station.cycle = SimpleNamespace(active=True)
    if blocked == "moving":
        station.boards = SimpleNamespace(conveyor=SimpleNamespace(snapshot=lambda: SimpleNamespace(
            connected=True, identified=True, error=None, telemetry={"BUSY": "1"})))
    with pytest.raises((RuntimeError, ValueError)):
        station.apply_camera_controls(CameraSettings(index=1 if blocked == "device" else 0))
    camera.apply_settings.assert_not_called()
