"""Camera alignment uses bounded, pause-restoring moves and cancellable setup."""
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.station import EdgeStation
from src.core.settings import SettingsStore
from src.core.camera_controls import slider_span, validate_slider_ranges


class AlignmentRig:
    def __init__(self):
        self.failure, self.calls, self.halts = "", [], 0
        self.early = None
        self.before_command = lambda role, text: None
        self.conveyor, self.egg, self.light = [self.Link(self, role) for role in
            ("CONVEYOR", "EGG_CONTROLLER", "LIGHT_CONTROLLER")]
        self.servo = self.egg
        self.links = (self.conveyor, self.egg, self.light)

    class Link:
        def __init__(self, rig, role):
            self.rig, self.role, self._status_complete = rig, role, True
            self.values = dict(FAULT="STARTUP_ACK_REQUIRED", BUSY="0", POSITION="0", SPEED="3000",
                               PAUSED="1", LIGHT="0", SENSOR="0")
        def snapshot(self):
            return SimpleNamespace(connected=True, identified=True, error="", telemetry=dict(self.values))
        def command(self, text, timeout=3):
            self.rig.calls.append((self.role, text, timeout))
            future = Future()
            try:
                self.rig.before_command(self.role, text)
                if text == "ACK_FAULT":
                    self.values["FAULT"] = "NONE"
                elif text.startswith("SPEED:"):
                    self.values["SPEED"] = text.split(":")[1]
                elif text in {"RESUME", "PAUSE"}:
                    self.rig.conveyor.values["PAUSED"] = str(int(text == "PAUSE"))
                elif text.startswith("JOG:"):
                    steps = int(text.split(":")[1]) if self.rig.early is None else self.rig.early
                    self.values["POSITION"] = str(int(self.values["POSITION"]) + steps)
                elif text.startswith("LIGHT_"):
                    self.values["LIGHT"] = str(int(text == "LIGHT_ON"))
                future.set_result(dict(self.values))
            except Exception as exc:
                future.set_exception(exc)
            return future

    def halt(self):
        self.halts += 1
    def stop(self):
        self.halt()


def alignment_station(tmp_path):
    station = EdgeStation(Mock(), Mock(), Mock(load_machine_state=Mock(return_value=None)),
                          "align", SettingsStore(tmp_path / "settings.json"))
    rig = station.boards = AlignmentRig()
    return station, rig


def test_prepare_then_bidirectional_jog_hold_and_finish_without_home_or_sort(tmp_path):
    station, rig = alignment_station(tmp_path)
    station.prepare_camera_alignment(True)
    assert rig.conveyor.values["SPEED"] == "5000" and rig.light.values["LIGHT"] == "1"
    assert rig.conveyor.values["PAUSED"] == "1"
    for steps in (25, -10):
        rig.calls.clear()
        message = station.jog_camera_cradle(steps)
        assert "Conveyor held" in message
        assert [text for _, text, _ in rig.calls] == ["STATUS", "RESUME", "STATUS", f"JOG:{steps}", "PAUSE"]
        assert rig.conveyor.values["PAUSED"] == "1"
    assert rig.conveyor.values["POSITION"] == "15"
    station.finish_camera_alignment()
    assert rig.light.values["LIGHT"] == "0" and station._camera_alignment_boards is None
    assert not station.calibrated
    with pytest.raises(RuntimeError, match="Connect for alignment"):
        station.jog_camera_cradle(25)
    station.inference.predict.assert_not_called()


@pytest.mark.parametrize("value", [0, 1001, -1001, True, 1.5])
def test_invalid_jog_never_dispatches(value, tmp_path):
    station, rig = alignment_station(tmp_path)
    with pytest.raises(ValueError):
        station.jog_camera_cradle(value)
    assert not rig.calls


def test_alignment_requires_inspection_and_idle_without_clearing_other_faults(tmp_path):
    station, rig = alignment_station(tmp_path)
    with pytest.raises(RuntimeError, match="path"):
        station.prepare_camera_alignment(False)
    assert not rig.calls
    station.cycle = SimpleNamespace(active=True)
    with pytest.raises(RuntimeError, match="Stop sorting"):
        station.prepare_camera_alignment(True)
    station.cycle = None
    rig.conveyor.values["FAULT"] = "FEED_LOCKOUT"
    with pytest.raises(RuntimeError, match="Inspect board faults"):
        station.prepare_camera_alignment(True)
    assert not rig.calls and rig.halts == 1


def test_stop_before_queued_setup_cannot_be_cleared_by_worker(tmp_path):
    station, rig = alignment_station(tmp_path)
    cancel = threading.Event()
    cancel.set()
    station.halt()
    with pytest.raises(RuntimeError, match="Setup stopped"):
        station.prepare_camera_alignment(True, cancel)
    assert not rig.calls


def test_stop_during_resume_never_dispatches_jog_or_retries(tmp_path):
    station, rig = alignment_station(tmp_path)
    station.prepare_camera_alignment(True)
    rig.calls.clear()
    cancel = threading.Event()
    def stop(role, text):
        if text == "RESUME":
            cancel.set()
            station.halt()
    rig.before_command = stop
    with pytest.raises(RuntimeError, match="Setup stopped"):
        station.jog_camera_cradle(25, cancel)
    assert [text for _, text, _ in rig.calls] == ["STATUS", "RESUME"]
    assert station._camera_alignment_boards is None


@pytest.mark.parametrize("failure", ["busy", "wire", "timeout", "overshoot", "pause"])
def test_failed_jog_halts_and_revokes_alignment(failure, tmp_path):
    station, rig = alignment_station(tmp_path)
    station.prepare_camera_alignment(True)
    rig.calls.clear()
    if failure == "busy":
        rig.conveyor.values["BUSY"] = "1"
    if failure == "overshoot":
        rig.early = 30
    def inject(role, text):
        if failure == "wire" and text == "RESUME":
            raise RuntimeError("broken pause wire")
        if failure == "timeout" and text.startswith("JOG:"):
            raise TimeoutError("command completion timeout")
        if failure == "pause" and text == "PAUSE":
            raise RuntimeError("pause failed")
    rig.before_command = inject
    with pytest.raises((RuntimeError, TimeoutError)):
        station.jog_camera_cradle(25)
    assert rig.halts and station._camera_alignment_boards is None
    assert len([text for _, text, _ in rig.calls if text.startswith("JOG:")]) <= 1


def test_sensor_early_stop_is_reported_then_held(tmp_path):
    station, rig = alignment_station(tmp_path)
    station.prepare_camera_alignment(True)
    rig.early = 7
    assert "sensor held the move early" in station.jog_camera_cradle(25)
    assert rig.conveyor.values["PAUSED"] == "1"


@pytest.mark.parametrize("ranges", [{"focus": [2, 1]}, {"focus": [float("nan"), 1]},
    {"unknown": [0, 1]}, {"focus": [0]}, {"focus": [False, 1]}, []])
def test_invalid_slider_spans_rejected(ranges):
    with pytest.raises(ValueError):
        validate_slider_ranges(ranges)


def test_custom_slider_span_roundtrip_preserves_outside_value_and_old_configs(tmp_path):
    station, _ = alignment_station(tmp_path)
    station.settings.camera.slider_ranges = {"focus": [-20, 120]}
    station.store.save(station.settings)
    assert station.store.load().camera.slider_ranges == {"focus": [-20, 120]}
    assert slider_span("focus", "opencv:0:DSHOW", 300) == (0, 300)
    assert slider_span("exposure", "opencv:0:DSHOW") == (-13, 0)
    assert slider_span("focus", "opencv:0:DSHOW", ranges={"focus": [-20, 120]}) == (-20, 120)
