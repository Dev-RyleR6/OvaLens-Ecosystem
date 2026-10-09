"""TASK-NEW-EDGE-SESSION-SYNC-01: closed runs, missing batches and replay fairness."""
from types import SimpleNamespace
from uuid import uuid4
from pathlib import Path
import sqlite3
import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from test_camera_preview_ui import preview_app
from test_startup_config import hidden_ui
from test_live_camera_ui import pump


def response(body, status=200):
    return SimpleNamespace(status_code=status, json=lambda: body)


class Backend:
    def __init__(self, db, monkeypatch):
        self.db, self.sessions, self.scans = db, {}, {}
        self.missing, self.calls, self.end_failure = set(), [], None
        monkeypatch.setattr("src.sync.sync_worker.requests.post", self.post)
        monkeypatch.setattr("src.sync.sync_worker.requests.put", self.put)
        monkeypatch.setattr("src.sync.sync_worker.requests.get", lambda *a, **k: response({}))

    def post(self, url, **kwargs):
        self.calls.append(url)
        data = kwargs["json"]
        if url.endswith("/sessions"):
            if data["batch_id"] in self.missing:
                return response({}, 404)
            self.sessions.setdefault(data["session_id"], {**data, "total_scanned": 0, "ended_at": None})
            return response(self.sessions[data["session_id"]])
        rows = data["scans"]
        inserted = 0
        for row in rows:
            if row["scan_id"] not in self.scans:
                self.scans[row["scan_id"]] = row
                self.sessions[row["session_id"]]["total_scanned"] += 1
                inserted += 1
        return response({"status": "success", "total_received": len(rows),
                         "synced_count": inserted, "duplicates_ignored": len(rows) - inserted})

    def put(self, url, **kwargs):
        self.calls.append(url)
        session_id = url.split("/")[-2]
        assert not self.db.get_uncommitted_scans(session_id=session_id)
        body = self.sessions[session_id]
        body["ended_at"] = kwargs["json"]["ended_at"]
        if self.end_failure == "lost":
            self.end_failure = None
            raise requests.ConnectionError("committed; response lost")
        if self.end_failure == "wrong_id":
            return response({**body, "session_id": str(uuid4())})
        if self.end_failure == "wrong_time":
            return response({**body, "ended_at": "2026-01-01T00:00:00+00:00"})
        if self.end_failure == "wrong_count":
            return response({**body, "total_scanned": 999})
        if self.end_failure == "missing":
            return response({}, 404)
        return response(body)


def local_run(db, batch="BATCH", count=1, closed=True):
    session_id = str(uuid4())
    db.create_session(session_id, batch, "DEVICE", "DAY_10", "Operator")
    for sequence in range(1, count + 1):
        db.record_scan(str(uuid4()), session_id, batch, sequence, "FERTILE", .8, 8, "ACCEPT", [])
    if closed:
        db.complete_session(session_id)
    return session_id


def test_completion_follows_all_metadata_packets_and_survives_restart(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    session_id = local_run(db, count=51)
    backend = Backend(db, monkeypatch)
    worker = BackgroundSyncWorker(db, api_key="test")
    worker._perform_sync()
    assert len(backend.scans) == 50 and not db.get_session_stats(session_id)["end_synced_at"]
    assert backend.sessions[session_id]["ended_at"] is None
    worker._perform_sync()
    assert len(backend.scans) == 51 and db.get_session_stats(session_id)["end_synced_at"]
    assert backend.sessions[session_id]["ended_at"] == db.get_session_stats(session_id)["ended_at"]
    calls = len(backend.calls)
    BackgroundSyncWorker(LocalDatabaseManager(db.db_path), api_key="test")._perform_sync()
    assert len(backend.calls) == calls


@pytest.mark.parametrize("failure", ["lost", "wrong_id", "wrong_time", "wrong_count", "missing"])
def test_completion_failure_keeps_durable_outbox_without_replaying_scans(tmp_path, monkeypatch, failure):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    session_id = local_run(db)
    backend = Backend(db, monkeypatch)
    backend.end_failure = failure
    worker = BackgroundSyncWorker(db, api_key="test")
    worker._perform_sync()
    assert not db.get_uncommitted_scans()
    assert not db.get_session_stats(session_id)["end_synced_at"]
    assert db.get_session_stats(session_id)["sync_error"] and worker.last_error
    backend.end_failure = None
    before = len([call for call in backend.calls if call.endswith("/sync")])
    BackgroundSyncWorker(LocalDatabaseManager(db.db_path), api_key="test")._perform_sync()
    assert db.get_session_stats(session_id)["end_synced_at"]
    assert len([call for call in backend.calls if call.endswith("/sync")]) == before


def test_missing_batch_is_explicit_and_does_not_starve_other_sessions(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    missing = [local_run(db, "MISSING") for _ in range(6)]
    ready = local_run(db, "READY")
    backend = Backend(db, monkeypatch)
    backend.missing.add("MISSING")
    worker = BackgroundSyncWorker(db, api_key="test")
    worker._perform_sync()
    assert "MISSING" in worker.last_error and "Dashboard > Batches" in worker.last_error
    worker._perform_sync()
    assert db.get_session_stats(ready)["end_synced_at"]
    assert db.get_unsynced_count() == 6
    assert all(db.get_session_stats(s)["total_scanned"] == 1 for s in missing)
    backend.missing.clear()
    for _ in range(2):
        worker._perform_sync()
    assert not db.get_unsynced_count() and not db.get_pending_session_ends()


def test_pre_upgrade_closed_runs_backfill_and_paused_runs_stay_open(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    closed = local_run(db)
    opened = local_run(db, closed=False)
    db.mark_scans_synced([row["scan_id"] for row in db.get_uncommitted_scans() if row["session_id"] == closed])
    backend = Backend(db, monkeypatch)
    prior = db.get_session_stats(closed)
    backend.sessions[closed] = {**prior, "total_scanned": 1}
    with sqlite3.connect(db.db_path) as conn:
        for column in ("end_synced_at", "sync_last_attempt_at", "sync_error"):
            conn.execute(f"ALTER TABLE local_sessions DROP COLUMN {column}")
    migrated = LocalDatabaseManager(db.db_path)
    BackgroundSyncWorker(migrated, api_key="test")._perform_sync()
    assert migrated.get_session_stats(closed)["end_synced_at"]
    assert not migrated.get_session_stats(opened)["ended_at"]
    assert backend.sessions[opened]["ended_at"] is None
    assert len(backend.scans) == 1  # Only the previously unsynced open run is sent.


def test_zero_scan_session_finishes_without_fabricating_scans(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    session_id = local_run(db, count=0)
    backend = Backend(db, monkeypatch)
    BackgroundSyncWorker(db, api_key="test")._perform_sync()
    assert not backend.scans and backend.sessions[session_id]["total_scanned"] == 0
    assert db.get_session_stats(session_id)["end_synced_at"]


def test_saved_office_selection_uses_actual_backend_batch_id(hidden_ui, tmp_path):
    import customtkinter as ctk
    app, _, _ = preview_app(tmp_path)
    app.sync_worker.fetch_active_batches = lambda: [{"batch_id": "KAY-SAMPLE-BATCH",
        "batch_code": "Kay Sample Batch", "breed": "KAYUMANGGI"}]
    app.operator_name = "Tester"
    def widgets(widget):
        for child in widget.winfo_children():
            yield child
            yield from widgets(child)
    try:
        app.deiconify()
        app.open_batch_setup_dialog()
        dialog = next(widget for widget in app.winfo_children() if isinstance(widget, ctk.CTkToplevel))
        pump(app, lambda: any(isinstance(widget, ctk.CTkOptionMenu)
            and "Kay Sample Batch (KAYUMANGGI)" in widget.cget("values") for widget in widgets(dialog)))
        office = next(widget for widget in widgets(dialog)
            if isinstance(widget, ctk.CTkButton) and "Office Batches" in str(widget.cget("text")))
        office.invoke()
        save = next(widget for widget in widgets(dialog)
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Save & Set Active Batch")
        app._animate_modal_close = lambda modal: modal.destroy()
        save.invoke()
        assert app.current_batch_id == "KAY-SAMPLE-BATCH"
        assert app.current_breed == "KAYUMANGGI"
    finally:
        app.shutdown()
        if app.winfo_exists():
            app.destroy()
