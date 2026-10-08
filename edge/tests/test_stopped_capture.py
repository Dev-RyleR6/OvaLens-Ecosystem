"""Stopped-only inference and exact-frame display regressions; no hardware."""
from pathlib import Path
from types import SimpleNamespace, MethodType
import sys
import time
import uuid
from unittest.mock import Mock

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.camera import CameraFrame
from src.core.sorting_cycle import ReviewRequired
from src.core.three_board_cycle import ThreeBoardCycle
from src.ui.app import OvaLensOperatorApp
from test_three_board import fixture, prediction
from test_operator_flow import operator


def held_cycle(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1)
    cycle._origin, cycle._last_egg_seq = 0, 1
    cycle.pending_capture = {"scan_id": str(uuid.uuid4())}
    rig.egg.values.update(STATE="HOLDING", PAUSED="1", EGG_SEQ="1")
    rig.conveyor.values.update(PAUSED="1")
    frames = []
    def snapshot(**kwargs):
        frame = CameraFrame(len(frames) + 1, time.monotonic(), 0,
                            np.full((120, 160, 3), len(frames) % 240, dtype=np.uint8))
        frames.append(frame)
        return frame
    cycle.camera.snapshot = snapshot
    cycle.camera.capture_fresh = lambda *args, **kwargs: snapshot()
    return cycle, rig


@pytest.mark.parametrize("result_hold", [0, 300, 1500])
def test_capture_waits_after_lamp_before_fresh_frame_and_inference(tmp_path, result_hold):
    """TASK-NEW-EDGE-CAPTURE-SETTLE-01: the result pause cannot shorten settling."""
    from src.core.settings import EdgeSettings
    cycle, rig = held_cycle(tmp_path)
    cycle.settings.calibration.settle_ms = EdgeSettings.three_board().calibration.settle_ms
    cycle.settings.calibration.hold_ms = result_hold
    events = []
    def settle(seconds):
        assert rig.light.values["LIGHT"] == "1"
        assert rig.egg.values["STATE"] == "HOLDING"
        assert rig.conveyor.values["PAUSED"] == "1"
        assert seconds == 1.5
        events.append("settle")
    cycle._delay = settle
    capture = cycle.camera.capture_fresh
    def fresh(drain, timeout):
        assert events == ["settle"] and drain == 6
        events.append("fresh")
        return capture(drain, timeout=timeout)
    cycle.camera.capture_fresh = fresh
    def predict(*args, **kwargs):
        assert events[:2] == ["settle", "fresh"]
        events.append("inference")
        return prediction()
    cycle.inference = SimpleNamespace(predict=predict)
    _, evidence = ThreeBoardCycle._capture(cycle)
    assert events == ["settle", "fresh", "inference", "inference", "inference"]
    assert evidence["settle_ms"] == 1500 and evidence["frames"] == 3
    assert evidence["span_ms"] >= 300
    assert not any(text == "RESUME" for _, text, _, _ in rig.trace)


def test_stop_during_longer_settle_prevents_capture_and_inference(tmp_path):
    import threading
    cycle, _ = held_cycle(tmp_path)
    cycle.settings.calibration.settle_ms = 1500
    cycle.camera.capture_fresh = Mock()
    cycle.inference = SimpleNamespace(predict=Mock())
    timer = threading.Timer(.05, cycle.stop)
    timer.start()
    try:
        with pytest.raises(RuntimeError, match="Operator stopped"):
            ThreeBoardCycle._capture(cycle)
        cycle.camera.capture_fresh.assert_not_called()
        cycle.inference.predict.assert_not_called()
        assert cycle.db.get_unsynced_count() == 0
    finally:
        timer.cancel()
        timer.join()


@pytest.mark.parametrize("change", ["busy", "pause", "sequence", "position", "lamp", "revision", "stop"])
def test_late_prediction_cannot_survive_changed_capture_conditions(tmp_path, change):
    cycle, rig = held_cycle(tmp_path)
    def predict(*args, **kwargs):
        if change == "busy":
            rig.conveyor.values["BUSY"] = "1"
        elif change == "pause":
            rig.egg.values["PAUSED"] = "0"
        elif change == "sequence":
            rig.egg.values["EGG_SEQ"] = "2"
        elif change == "position":
            rig.conveyor.values["POSITION"] = "1"
        elif change == "lamp":
            rig.light.values["LIGHT"] = "0"
        elif change == "revision":
            cycle.camera.settings_revision += 1
        else:
            cycle.stop()
        return prediction()
    cycle.inference = SimpleNamespace(predict=Mock(side_effect=predict))
    with pytest.raises(RuntimeError):
        ThreeBoardCycle._capture(cycle)
    assert cycle.inference.predict.call_count == 1
    assert cycle.capture_view is None
    assert "prediction" not in cycle.pending_capture
    assert cycle.db.get_unsynced_count() == 0
    assert not any(text == "RESUME" for _, text, _, _ in rig.trace)


def test_moving_conveyor_never_starts_lamp_or_inference(tmp_path):
    cycle, rig = held_cycle(tmp_path)
    rig.conveyor.values["BUSY"] = "1"
    cycle.inference = SimpleNamespace(predict=Mock())
    with pytest.raises(RuntimeError, match="stationary"):
        ThreeBoardCycle._capture(cycle)
    assert not rig.trace
    cycle.inference.predict.assert_not_called()


@pytest.mark.parametrize("reason", ["confidence", "disagreement", "empty", "timeout"])
def test_review_retains_image_paired_with_last_prediction(tmp_path, reason):
    import cv2
    cycle, rig = held_cycle(tmp_path)
    calls = []
    def predict(image, **kwargs):
        calls.append(image)
        if reason == "timeout":
            raise TimeoutError("Inference deadline")
        result = prediction("INFERTILE" if reason == "disagreement" and len(calls) == 2 else "FERTILE",
                            .5 if reason == "confidence" else .94)
        if reason == "empty":
            result = prediction(None)
        return {**result, "pixel": int(image[0, 0, 0])}
    cycle.inference = SimpleNamespace(predict=predict)
    with pytest.raises((ReviewRequired, TimeoutError)):
        ThreeBoardCycle._capture(cycle)
    view = cycle.capture_view
    assert view is not None
    image = cv2.imread(cycle.pending_capture["image_path"])
    assert np.array_equal(image, view.frame.image)
    assert cycle.pending_capture["frame"] == view.identity()
    if reason != "timeout":
        assert view.result["pixel"] == int(view.frame.image[0, 0, 0])
        assert cycle.pending_capture["prediction"] == view.result
    else:
        assert view.result == {}
    assert len(calls) == (2 if reason == "disagreement" else 1)
    assert cycle.db.get_unsynced_count() == 0
    cycle.stop()
    assert cycle.capture_view is None


def test_diagnostic_is_blocked_during_motion_and_late_motion_discards_result(tmp_path):
    app = operator(tmp_path)
    state = SimpleNamespace(connected=True, identified=True, error=None, telemetry={"BUSY": "1"})
    app.station = SimpleNamespace(cycle=None, boards=SimpleNamespace(
        conveyor=SimpleNamespace(snapshot=lambda: state)))
    app.trigger_candling_scan()
    app.inference_worker.submit.assert_not_called()
    state.telemetry["BUSY"] = "0"
    frame = CameraFrame(3, time.monotonic(), 0, np.zeros((20, 20, 3)))
    app.camera.snapshot.return_value = frame
    app.trigger_candling_scan()
    state.telemetry["BUSY"] = "1"
    app.inference_worker.result_queue.put({**prediction(), "request_id": app._inference_request_id})
    app._drain_predictions()
    assert app._diagnostic_view is None and not app._jobs.work


def test_diagnostic_result_is_paired_with_submitted_frame(tmp_path):
    app = operator(tmp_path)
    frame = CameraFrame(3, time.monotonic(), 0, np.zeros((20, 20, 3)))
    app.camera.snapshot.return_value = frame
    app.trigger_candling_scan()
    app.camera.snapshot.return_value = CameraFrame(4, time.monotonic(), 0, np.ones((20, 20, 3)))
    app.inference_worker.result_queue.put({**prediction(), "request_id": app._inference_request_id})
    app._drain_predictions()
    assert app._diagnostic_view.frame is frame
    app._jobs.finish()
    app.camera.is_running = True
    assert OvaLensOperatorApp._get_display_capture(app) is app._diagnostic_view


def test_viewport_clears_box_without_waiting_for_a_new_camera_frame(monkeypatch):
    from src.core.capture_view import CaptureView
    frame = CameraFrame(1, time.monotonic(), 0, np.zeros((120, 160, 3), dtype=np.uint8))
    view = CaptureView.create(frame, prediction())
    cycle = SimpleNamespace(status={"state": "DISPLAYING"}, capture_view=view)
    app = SimpleNamespace(_closing=False, _stopping=False, _current_photo=None,
        camera=SimpleNamespace(is_running=True, snapshot=lambda **kwargs: frame),
        station=SimpleNamespace(cycle=cycle), is_auto_cycle_running=True,
        _cached_container_w=320, _cached_container_h=240, show_crosshairs=False,
        video_label=Mock(), _log=Mock(), after=Mock())
    app._get_display_capture = MethodType(OvaLensOperatorApp._get_display_capture, app)
    app._update_video_frame = MethodType(OvaLensOperatorApp._update_video_frame, app)
    monkeypatch.setattr("src.ui.app.ImageTk.PhotoImage", lambda image: np.asarray(image))
    app._update_video_frame()
    assert np.count_nonzero(app._current_photo) > 0
    app._update_video_frame()
    assert app.video_label.configure.call_count == 1  # Reuse unchanged captured rendering.
    cycle.capture_view = None
    cycle.status = {"state": "SEARCHING"}
    app._update_video_frame()
    assert app.video_label.configure.call_count == 2
    assert np.count_nonzero(app._current_photo) == 0  # Same camera sequence, no stale box.
    app.camera.snapshot = lambda **kwargs: None
    app._update_video_frame()
    assert app._current_photo is None
    app.video_label.configure.assert_called_with(image="")
    app.camera.snapshot = lambda **kwargs: frame
    app._update_video_frame()
    assert app.video_label.configure.call_count == 4  # Restoring the same sequence redraws.
    app._log.assert_not_called()
