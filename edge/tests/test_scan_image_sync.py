"""Durable image outbox and exact manual capture evidence; hardware-free."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import sqlite3
import sys
import time

import cv2
import numpy as np
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.camera import CameraFrame
from src.core.capture_view import CaptureView
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from src.ui.app import OvaLensOperatorApp
from test_operation_safety import station, prediction


def saved_scan(tmp_path, count=1):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    session_id = str(uuid4())
    db.create_session(session_id, "BATCH", "DEVICE", "DAY_10", "Operator")
    ids = []
    for sequence in range(1, count + 1):
        scan_id = str(uuid4())
        path = db.save_scan_image(scan_id, np.full((20, 30, 3), sequence, dtype=np.uint8))
        db.record_scan(scan_id, session_id, "BATCH", sequence, "FERTILE", .9, 10, "ACCEPT", [], path)
        ids.append(scan_id)
    worker = BackgroundSyncWorker(db, api_key="test-key")
    worker._registered_sessions.add(session_id)
    return db, worker, ids


def upload_ack(kwargs):
    data = kwargs["files"]["file"][1]
    scan_id = kwargs["data"]["scan_id"]
    return {"status": "success", "scan_id": scan_id, "image_url": f"/storage/{scan_id}.jpg",
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def network(monkeypatch, image_reply=None):
    sent = []
    def post(url, **kwargs):
        sent.append((url, kwargs))
        if url.endswith("/sync"):
            size = len(kwargs["json"]["scans"])
            body = {"status": "success", "total_received": size, "synced_count": size, "duplicates_ignored": 0}
        else:
            body = image_reply(kwargs) if image_reply else upload_ack(kwargs)
        return SimpleNamespace(status_code=200, json=lambda: body)
    monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
    monkeypatch.setattr("src.sync.sync_worker.requests.get", lambda *a, **k: SimpleNamespace(status_code=200))
    return sent


def test_metadata_precedes_exact_jpeg_upload_and_both_are_acknowledged(tmp_path, monkeypatch):
    db, worker, ids = saved_scan(tmp_path)
    assert not db.get_pending_scan_images() and db.get_unsynced_count() == 1
    sent = network(monkeypatch)
    worker._perform_sync()
    assert [url.rsplit("/", 1)[1] for url, _ in sent] == ["sync", "upload-image"]
    upload = sent[1][1]
    assert upload["headers"] == {"X-API-Key": "test-key"}
    assert upload["files"]["file"][1] == (tmp_path / "local_scans" / f"{ids[0]}.jpg").read_bytes()
    assert db.get_unsynced_count() == 0 and worker.total_synced == 1
    assert db.get_recent_scans()[0]["is_synced"] == 1
    assert LocalDatabaseManager(db.db_path).get_pending_scan_images() == []


@pytest.mark.parametrize("field,value", [("scan_id", str(uuid4())), ("sha256", "wrong"),
    ("image_url", "/storage/wrong.jpg"), ("size_bytes", 0), ("status", "pending")])
def test_bad_image_ack_survives_restart_without_resending_metadata(tmp_path, monkeypatch, field, value):
    db, worker, ids = saved_scan(tmp_path)
    def bad_ack(kwargs):
        return {**upload_ack(kwargs), field: value}
    network(monkeypatch, bad_ack)
    worker._perform_sync()
    assert not db.get_uncommitted_scans() and db.get_unsynced_count() == 1
    assert db.get_recent_scans()[0]["is_synced"] == 0
    assert db.get_pending_scan_images()[0]["image_sync_error"]
    restarted = BackgroundSyncWorker(LocalDatabaseManager(db.db_path), api_key="test-key")
    sent = network(monkeypatch)
    restarted._perform_sync()
    assert len(sent) == 1 and sent[0][0].endswith("/upload-image")
    assert db.get_unsynced_count() == 0


def test_lost_upload_ack_retries_same_bytes_after_restart(tmp_path, monkeypatch):
    db, worker, ids = saved_scan(tmp_path)
    received = []
    def lose_ack(kwargs):
        received.append(kwargs["files"]["file"][1])
        raise requests.ConnectionError("response lost")
    network(monkeypatch, lose_ack)
    worker._perform_sync()
    assert db.get_unsynced_count() == 1 and not worker.is_online
    sent = network(monkeypatch)
    BackgroundSyncWorker(LocalDatabaseManager(db.db_path), api_key="test-key")._perform_sync()
    assert received[0] == sent[0][1]["files"]["file"][1]
    assert db.get_unsynced_count() == 0


def test_missing_image_does_not_starve_other_photos_and_stop_bounds_replay(tmp_path, monkeypatch):
    db, worker, ids = saved_scan(tmp_path, count=7)
    (tmp_path / "local_scans" / f"{ids[0]}.jpg").unlink()
    sent = network(monkeypatch)
    worker._perform_sync()
    assert len(sent) == 5 and db.get_unsynced_count() == 3  # metadata plus four successful photos
    worker._perform_sync()
    assert db.get_unsynced_count() == 1
    assert db.get_pending_scan_images()[0]["scan_id"] == ids[0]
    worker.stop()
    before = len(sent)
    worker._sync_images()
    assert len(sent) == before


def test_outbox_migrates_already_synced_photos_without_replaying_metadata(tmp_path, monkeypatch):
    db, worker, ids = saved_scan(tmp_path)
    db.mark_scans_synced(ids)
    with sqlite3.connect(db.db_path) as conn:
        conn.execute("DROP INDEX idx_scan_image_outbox")
        for column in ("image_synced_at", "image_url", "image_sync_error", "image_last_attempt_at"):
            conn.execute(f"ALTER TABLE local_scans DROP COLUMN {column}")
    migrated = LocalDatabaseManager(db.db_path)
    assert migrated.get_unsynced_count() == 1
    assert not migrated.get_uncommitted_scans()
    sent = network(monkeypatch)
    BackgroundSyncWorker(migrated, api_key="test-key")._perform_sync()
    assert len(sent) == 1 and migrated.get_unsynced_count() == 0


def test_outbox_rejects_file_outside_evidence_directory(tmp_path, monkeypatch):
    db, worker, ids = saved_scan(tmp_path)
    db.mark_scans_synced(ids)
    other = tmp_path / "unrelated.jpg"
    other.write_bytes(b"private")
    with db._get_connection() as conn:
        conn.execute("UPDATE local_scans SET image_path = ?", (str(other),))
    sent = network(monkeypatch)
    worker._perform_sync()
    assert not sent and db.get_unsynced_count() == 1
    assert "path" in db.get_pending_scan_images()[0]["image_sync_error"]


def test_manual_scan_saves_exact_paired_frame_on_disk_worker(tmp_path):
    app = station(tmp_path)
    pixels = np.full((20, 30, 3), 87, dtype=np.uint8)
    app._diagnostic_view = CaptureView.create(CameraFrame(8, time.monotonic(), 2, pixels), prediction())
    OvaLensOperatorApp._process_scan_result(app, prediction())
    assert not list(tmp_path.glob("local_scans/*.jpg")) and app.total_count == 0
    # Preview may change while the write waits; the captured photo must not.
    app._diagnostic_view = None
    app._jobs.finish()
    row = app.db.get_uncommitted_scans()[0]
    assert np.array_equal(cv2.imread(row["image_path"]), pixels)
    assert app.total_count == 1 and app.iot.mock_calls == []


def test_failed_manual_photo_write_does_not_commit_scan_or_counts(tmp_path, monkeypatch):
    app = station(tmp_path)
    app._diagnostic_view = CaptureView.create(CameraFrame(8, time.monotonic(), 0,
        np.zeros((20, 20, 3), dtype=np.uint8)), prediction())
    monkeypatch.setattr(app.db, "save_scan_image", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    OvaLensOperatorApp._process_scan_result(app, prediction())
    app._jobs.finish()
    assert app.total_count == 0 and not app.db.get_uncommitted_scans()
