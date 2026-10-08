"""Operator request lifecycle regressions; no camera, serial, or network hardware."""
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import queue
import sys
import threading
import time
import tkinter as tk

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.inference_worker import InferenceWorker
from src.core.camera import CameraFrame
from src.core.operator_flow import OperatorState, validate_batch_config
from src.ui.app import OvaLensOperatorApp
from test_operation_safety import station, prediction


def operator(tmp_path):
    app = station(tmp_path)
    app._scan_busy = False
    app._pending_prediction = app._inference_request_id = app._pending_finalization_id = None
    app._finalization_failed = app._diagnostics_complete = False
    app._stop_cycle_event = threading.Event()
    app.chamber = None
    app.is_auto_cycle_running = False
    app.camera = SimpleNamespace(is_mock_mode=False, is_running=False, last_error=None,
                                 start=Mock(), stop=Mock(), settings_revision=0, snapshot=Mock(return_value=None))
    app.inference_worker = SimpleNamespace(busy=False, submit=Mock(), result_queue=queue.Queue())
    app.grab_current = Mock(return_value=None)
    app.open_batch_completion_modal = Mock()
    app.standby_frame = Mock()
    app.video_label = Mock()
    app._render_standby_hud = Mock()
    app._update_cycle_hud = Mock()
    app.timers = []
    app.after = lambda delay, work: app.timers.append((delay, work))
    for name in ("_set_operation_state", "_await_scan_frame", "_prediction_timeout",
                 "_drain_predictions", "trigger_candling_scan", "stop_or_cancel_session",
                 "_process_scan_result"):
        setattr(app, name, MethodType(getattr(OvaLensOperatorApp, name), app))
    return app


def test_one_click_waits_for_fresh_frame_and_rejects_duplicate_click(tmp_path):
    app = operator(tmp_path)
    app.trigger_candling_scan()
    assert app._operator_state == OperatorState.CAMERA_STARTING
    app.trigger_candling_scan()
    app.camera.start.assert_called_once()
    app.inference_worker.submit.assert_not_called()
    app.camera.snapshot.return_value = CameraFrame(1, time.monotonic(), 0, np.zeros((20, 20, 3), dtype=np.uint8))
    app.timers.pop(0)[1]()
    assert app._operator_state == OperatorState.CLASSIFYING
    app.inference_worker.submit.assert_called_once()
    assert not app._jobs.work  # inference must not occupy the storage worker


def test_camera_timeout_and_cancel_do_not_submit_stale_frame(tmp_path):
    app = operator(tmp_path)
    app.trigger_candling_scan()
    app._await_scan_frame(0, time.monotonic() - 1)
    assert not app._scan_busy and app._operator_state == OperatorState.ERROR
    app._operation_generation += 1
    app.camera.snapshot.return_value = CameraFrame(1, time.monotonic(), 0, np.zeros((20, 20, 3)))
    app.timers.pop(0)[1]()
    app.inference_worker.submit.assert_not_called()


def test_timeout_discards_late_result_and_model_busy_blocks_more_requests(tmp_path):
    app = operator(tmp_path)
    app.camera.snapshot.return_value = CameraFrame(1, time.monotonic(), 0, np.zeros((20, 20, 3)))
    app.trigger_candling_scan()
    request_id = app._inference_request_id
    app.inference_worker.busy = True
    app._prediction_timeout(request_id, 0)
    assert app._operator_state == OperatorState.REVIEW and not app._scan_busy
    app.trigger_candling_scan()
    app.inference_worker.submit.assert_called_once()
    app.inference_worker.result_queue.put({**prediction(), "request_id": request_id})
    app._drain_predictions()
    assert not app._jobs.work and app.total_count == 0


def test_correlated_prediction_saves_then_stops_at_diagnostic_target(tmp_path):
    app = operator(tmp_path)
    app.target_egg_count = 1
    app.camera.snapshot.return_value = CameraFrame(1, time.monotonic(), 0, np.zeros((20, 20, 3)))
    app.trigger_candling_scan()
    request_id = app._inference_request_id
    app.inference_worker.result_queue.put({**prediction(), "request_id": "obsolete"})
    app._drain_predictions()
    assert not app._jobs.work
    app.inference_worker.result_queue.put({**prediction(), "request_id": request_id})
    app._drain_predictions()
    assert app._operator_state == OperatorState.SAVING and app.total_count == 0
    app._jobs.finish()
    assert app.total_count == 1 and app._stopping
    app._jobs.finish()
    assert app._operator_state == OperatorState.COMPLETE
    app.trigger_candling_scan()
    app.inference_worker.submit.assert_called_once()
    assert app.db.get_session_stats(app._last_session_id)["ended_at"]


def test_finalization_failure_preserves_identity_and_retry_completes(tmp_path, monkeypatch):
    app = operator(tmp_path)
    app._process_scan_result(prediction())
    app._jobs.finish()
    session_id = app.current_session_id
    complete = app.db.complete_session
    monkeypatch.setattr(app.db, "complete_session", Mock(side_effect=OSError("disk full")))
    app.stop_or_cancel_session()
    app._jobs.finish()
    assert app._operator_state == OperatorState.RECOVERY
    assert app.current_session_id == app._pending_finalization_id == session_id
    app.trigger_candling_scan()
    app.inference_worker.submit.assert_not_called()
    monkeypatch.setattr(app.db, "complete_session", complete)
    app.stop_or_cancel_session()
    app._jobs.finish()
    assert app.current_session_id is None and not app._finalization_failed
    assert app._last_session_id == session_id


def test_stop_recovers_counts_from_scan_committed_before_cancelled_callback(tmp_path):
    app = operator(tmp_path)
    app._process_scan_result(prediction())
    work, success, _ = app._jobs.work.pop(0)
    record = work()
    app.stop_or_cancel_session()
    success(record)  # old UI callback must not revive the session
    assert app.total_count == 0
    app._jobs.finish()
    assert app.total_count == app.infertile_count == 1
    assert not app.is_session_active and app.current_session_id is None


def test_cancel_before_first_write_finishes_without_false_recovery(tmp_path):
    app = operator(tmp_path)
    app._process_scan_result(prediction())
    session_id = app.current_session_id
    app.stop_or_cancel_session()
    app._jobs.finish()  # cancelled persistence request
    app._jobs.finish()  # healthy lookup finds that no session was created
    assert app._operator_state == OperatorState.READY
    assert not app._finalization_failed and app.current_session_id is None
    assert app.db.get_session_stats(session_id) == {}
    assert app.db.get_unsynced_count() == 0


def test_inference_worker_retains_request_id_and_does_not_queue_overlapping_calls():
    entered, release = threading.Event(), threading.Event()
    def predict(frame):
        entered.set()
        release.wait(2)
        return prediction()
    worker = InferenceWorker(SimpleNamespace(predict=predict))
    worker.start()
    try:
        worker.submit(np.zeros((20, 20, 3)), "request-1")
        assert entered.wait(1)
        with pytest.raises(RuntimeError):
            worker.submit(np.zeros((20, 20, 3)), "request-2")
        release.set()
        assert worker.result_queue.get(timeout=1)["request_id"] == "request-1"
    finally:
        release.set()
        worker.stop()


def test_space_in_editor_or_open_dialog_does_not_start_scan():
    app = SimpleNamespace(grab_current=Mock(return_value=None), trigger_candling_scan=Mock())
    editor = Mock(spec=tk.Entry)
    editor.winfo_toplevel.return_value = app
    OvaLensOperatorApp._scan_shortcut(app, SimpleNamespace(widget=editor))
    app.trigger_candling_scan.assert_not_called()
    widget = Mock()
    widget.winfo_toplevel.return_value = app
    app.grab_current.return_value = object()
    OvaLensOperatorApp._scan_shortcut(app, SimpleNamespace(widget=widget))
    app.trigger_candling_scan.assert_not_called()


@pytest.mark.parametrize("quantity", ["abc", "0", "-2", "100001", "1.5", True])
def test_batch_validation_rejects_invalid_targets(quantity):
    with pytest.raises(ValueError):
        validate_batch_config("BATCH", "Operator", quantity, "DAY_10")


def test_batch_validation_requires_operator_and_day_ten():
    with pytest.raises(ValueError):
        validate_batch_config("BATCH", " ", "10", "DAY_10")
    with pytest.raises(ValueError):
        validate_batch_config("BATCH", "Operator", "10", "DAY_18")
    assert validate_batch_config(" BATCH ", " Operator ", "10", "DAY_10") == ("BATCH", "Operator", 10)


def test_scan_cannot_attach_to_another_batch_or_a_finished_session(tmp_path):
    app = operator(tmp_path)
    app.db.create_session("s", "original", "d", "DAY_10", "operator")
    def save(batch):
        app.db.record_scan("scan", "s", batch, 1, "FERTILE", .9, 12, "ACCEPT", [])
    with pytest.raises(ValueError, match="open session"):
        save("different")
    app.db.complete_session("s")
    with pytest.raises(ValueError, match="open session"):
        save("original")
    assert app.db.get_unsynced_count() == 0
    assert app.db.get_session_stats("s")["total_scanned"] == 0
