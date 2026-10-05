"""TASK-NEW-EDGE-AUDIT-01: failure and cancellation contracts, no hardware."""
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import csv
import queue
import sqlite3
import sys
import threading
import time

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.background_jobs import BackgroundJobs
from src.core.camera import CameraGrabber
from src.core.chamber_controller import ChamberController
from src.core.inference import InferenceEngine
from src.core.inference_worker import InferenceWorker
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from src.ui.app import OvaLensOperatorApp
from src.ui.startup_config import StartupConfigWindow


def test_csv_export_keeps_all_rows_and_identifiers_inside_output_dir(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    batch_id = "../../other\\batch"
    db.create_session("s", batch_id, "d", "DAY_10", "operator")
    with db._get_connection() as conn:
        conn.executemany("""INSERT INTO local_scans
            (scan_id, session_id, batch_id, sequence_number, final_class,
             confidence, inference_ms, routing_action, scanned_at)
            VALUES (?, 's', ?, ?, 'FERTILE', .9, 10, 'ACCEPT', '2026-10-06')""",
            [(str(i), batch_id, i) for i in range(10001)])
        conn.commit()
    output = tmp_path / "reports"
    for path in (db.export_batch_csv(batch_id, output_dir=str(output)),
                 db.export_session_csv("s", output_dir=str(output))):
        assert Path(path).resolve().parent == output.resolve()
        with open(path, encoding="utf-8", newline="") as report:
            assert len(list(csv.reader(report))) == 10002


def test_empty_onnx_detection_is_unknown_and_uses_fp16_input():
    engine = object.__new__(InferenceEngine)
    engine.imgsz = 32
    engine.conf_threshold = 0.7
    engine.onnx_session = Mock()
    engine.onnx_session.get_inputs.return_value = [SimpleNamespace(name="image", type="tensor(float16)")]
    engine.onnx_session.run.return_value = [np.zeros((1, 6, 1), dtype=np.float16)]
    result = engine._infer_onnx(np.zeros((32, 32, 3), dtype=np.uint8))
    assert result["final_class"] is None
    assert result["routing_action"] == "MANUAL_REVIEW"
    assert result["confidence"] == 0
    assert engine.onnx_session.run.call_args.args[1]["image"].dtype == np.float16


def test_empty_pytorch_detection_is_not_infertile():
    engine = object.__new__(InferenceEngine)
    engine.yolo_model = Mock()
    engine.yolo_model.predict.return_value = []
    engine.imgsz, engine.conf_threshold = 32, 0.7
    assert engine._infer_pytorch(np.zeros((32, 32, 3), dtype=np.uint8))["final_class"] is None


def test_camera_failure_never_switches_to_synthetic_frames(monkeypatch):
    capture = Mock()
    capture.isOpened.return_value = False
    monkeypatch.setattr("src.core.camera.cv2.VideoCapture", lambda *args: capture)
    camera = CameraGrabber()
    camera.start()
    camera._thread.join(timeout=2)
    assert not camera.is_running
    assert not camera.is_mock_mode
    assert camera.get_latest_frame() is None
    assert "unavailable" in camera.last_error
    assert capture.release.call_count >= 1


def test_camera_stale_frame_cannot_be_used_for_a_scan():
    camera = CameraGrabber()
    camera._is_running = True
    camera._latest_frame = np.zeros((2, 2, 3), dtype=np.uint8)
    camera._last_frame_at = time.monotonic() - 1
    assert camera.get_latest_frame() is None


def test_inference_exception_is_returned_as_review_not_silently_lost():
    engine = Mock()
    engine.predict.side_effect = RuntimeError("model error")
    worker = InferenceWorker(engine)
    worker.start()
    try:
        worker.frame_queue.put(np.zeros((2, 2, 3), dtype=np.uint8))
        result = worker.result_queue.get(timeout=2)
        assert result["final_class"] is None
        assert result["error_code"] == "INFERENCE_ERROR"
        assert result["routing_action"] == "MANUAL_REVIEW"
    finally:
        worker.stop()
        worker._thread.join(timeout=1)


def test_jobs_deliver_callbacks_on_the_caller_thread():
    jobs = BackgroundJobs()
    entered = threading.Event()
    ids = []
    caller = threading.get_ident()
    def work():
        entered.set()
        return threading.get_ident()
    jobs.submit(work, lambda worker_id: ids.append((worker_id, threading.get_ident())), pytest.fail)
    assert entered.wait(1)
    jobs.pending.join()
    assert ids == []
    jobs.drain()
    assert ids[0][0] != caller
    assert ids[0][1] == caller
    jobs.close()


class DeferredJobs:
    def __init__(self):
        self.work = []
    def submit(self, work, success, error):
        self.work.append((work, success, error))
    def finish(self):
        work, success, error = self.work.pop(0)
        try:
            value = work()
        except Exception as exc:
            error(str(exc))
        else:
            success(value)


def station(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "station.db"))
    app = SimpleNamespace(
        _closing=False, _stopping=False, _scan_busy=True, _operation_generation=0,
        simulation=False, camera=SimpleNamespace(is_mock_mode=False),
        _jobs=DeferredJobs(), db=db, iot=Mock(), current_session_id=None,
        current_batch_id="TEST-BATCH", device_id="TEST-STATION", current_stage="DAY_10",
        operator_name="Tester", scan_sequence=0, _session_start_time=None,
        total_count=0, fertile_count=0, infertile_count=0, review_count=0,
        _log=Mock(), _set_session_active_state=Mock(), _update_counters_ui=Mock(),
        _update_result_banner=Mock(), is_session_active=False, target_egg_count=100,
        _set_operation_state=Mock(), result_title=Mock(), result_badge=Mock(),
        result_subtitle=Mock())
    app._scan_failed = MethodType(OvaLensOperatorApp._scan_failed, app)
    return app


def prediction(confidence=0.9):
    return {"final_class": "INFERTILE", "confidence": confidence, "routing_action": "REJECT",
            "inference_ms": 12, "detections": [{"class": "INFERTILE"}], "engine": "ONNX test"}


def test_record_is_committed_before_counters_and_never_actuated(tmp_path):
    app = station(tmp_path)
    OvaLensOperatorApp._process_scan_result(app, prediction())
    assert app.total_count == 0
    assert app.db.get_unsynced_count() == 0
    app._jobs.finish()
    assert app.db.get_unsynced_count() == 1
    assert app.total_count == 1 and app.infertile_count == 1
    assert app.iot.mock_calls == []


def test_storage_failure_keeps_counts_and_routes_unchanged_and_retry_works(tmp_path, monkeypatch):
    app = station(tmp_path)
    record = app.db.record_scan
    monkeypatch.setattr(app.db, "record_scan", Mock(side_effect=OSError("disk full")))
    OvaLensOperatorApp._process_scan_result(app, prediction())
    app._jobs.finish()
    assert app.total_count == 0 and app.scan_sequence == 0
    assert app.iot.mock_calls == []
    monkeypatch.setattr(app.db, "record_scan", record)
    OvaLensOperatorApp._process_scan_result(app, prediction())
    app._jobs.finish()
    assert app.total_count == 1 and app.db.get_unsynced_count() == 1


def test_cancelled_scan_does_not_write_or_update_ui(tmp_path):
    app = station(tmp_path)
    OvaLensOperatorApp._process_scan_result(app, prediction())
    app._operation_generation += 1
    app._jobs.finish()
    assert app.db.get_unsynced_count() == 0 and app.total_count == 0


@pytest.mark.parametrize("kind", ["unknown", "simulation", "fallback"])
def test_untrustworthy_results_are_not_saved(tmp_path, kind):
    app = station(tmp_path)
    result = prediction()
    if kind == "unknown":
        result["final_class"] = None
    elif kind == "simulation":
        app.simulation = True
    else:
        result["engine"] = "HEURISTIC_SIMULATION"
    OvaLensOperatorApp._process_scan_result(app, result)
    assert not app._jobs.work
    assert app.db.get_unsynced_count() == 0
    assert app.iot.mock_calls == []


def test_low_confidence_is_review_in_both_ui_and_database(tmp_path):
    app = station(tmp_path)
    OvaLensOperatorApp._process_scan_result(app, prediction(0.6))
    app._jobs.finish()
    assert app.review_count == 1 and app.infertile_count == 0
    stats = app.db.get_session_stats(app.current_session_id)
    assert stats["manual_review_count"] == 1 and stats["infertile_count"] == 0


def test_legacy_cycle_cannot_issue_motor_commands():
    motor = Mock()
    controller = ChamberController(motor, Mock(), queue.Queue(), queue.Queue())
    with pytest.raises(RuntimeError, match="disabled"):
        controller.run(1, 10, 10, 250)
    controller.stop()
    assert motor.mock_calls == []


@pytest.mark.parametrize("speed,distance,pulse", [("nan", "25", "250"), ("12", "-1", "250"),
                                                 ("12", "25", "0")])
def test_startup_rejects_unsafe_numeric_configuration(speed, distance, pulse):
    app = SimpleNamespace(result=None, _status_label=Mock())
    for field, value in (("_count_entry", "10"), ("_operator_entry", "Tester"),
                         ("_speed_entry", speed), ("_dist_entry", distance),
                         ("_display_ms_entry", "1200"), ("_pulse_entry", pulse)):
        setattr(app, field, SimpleNamespace(get=lambda v=value: v))
    app._port_var = SimpleNamespace(get=lambda: "Auto-Detect")
    StartupConfigWindow._on_start(app)
    assert app.result is None
    assert app._status_label.configure.called


@pytest.mark.parametrize("ack,status", [({}, 200), ({"status": "success", "total_received": 1,
    "synced_count": 0, "duplicates_ignored": 0}, 200), ({}, 422)])
def test_sync_rejection_or_partial_ack_never_clears_local_record(tmp_path, monkeypatch, ack, status):
    app = station(tmp_path)
    OvaLensOperatorApp._process_scan_result(app, prediction())
    app._jobs.finish()
    worker = BackgroundSyncWorker(app.db, api_key="test-key")
    worker._registered_sessions.add(app.current_session_id)
    monkeypatch.setattr("src.sync.sync_worker.requests.post", lambda *a, **k:
                        SimpleNamespace(status_code=status, json=lambda: ack))
    worker._perform_sync()
    assert app.db.get_unsynced_count() == 1
    assert worker.last_error


def test_duplicate_sync_ack_is_safe_and_session_identity_is_preserved(tmp_path, monkeypatch):
    app = station(tmp_path)
    OvaLensOperatorApp._process_scan_result(app, prediction())
    app._jobs.finish()
    sent = []
    def post(url, **kwargs):
        sent.append(kwargs["json"])
        if url.endswith("/sessions"):
            return SimpleNamespace(status_code=200, json=lambda: kwargs["json"])
        return SimpleNamespace(status_code=200, json=lambda: {
            "status": "success", "total_received": 1, "synced_count": 0, "duplicates_ignored": 1})
    monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
    worker = BackgroundSyncWorker(app.db, api_key="test-key")
    worker._perform_sync()
    assert sent[0]["device_id"] == app.device_id
    assert sent[0]["operator_name"] == app.operator_name
    assert app.db.get_unsynced_count() == 0


def test_migration_is_once_only_when_legacy_column_cannot_be_dropped(tmp_path):
    connection = sqlite3.connect(tmp_path / "legacy.db")
    connection.execute("CREATE TABLE local_sessions (infertile_count INTEGER, abnormal_count INTEGER, stage TEXT)")
    connection.execute("INSERT INTO local_sessions VALUES (3, 2, 'DAY_18')")
    connection.execute("CREATE TABLE local_scans (final_class TEXT)")
    class OldSQLite:
        def execute(self, sql, *args):
            if "DROP COLUMN" in sql:
                raise sqlite3.OperationalError("unsupported")
            return connection.execute(sql, *args)
    LocalDatabaseManager._migrate_legacy_contract(OldSQLite())
    LocalDatabaseManager._migrate_legacy_contract(OldSQLite())
    assert connection.execute("SELECT infertile_count FROM local_sessions").fetchone()[0] == 5
    connection.close()
