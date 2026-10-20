"""TASK-NEW-EDGE-BATCH-CREATE-01: offline batch identity and ordered replay."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.batches import new_batch_record
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from test_session_sync import Backend, local_run, response


def batch(**changes):
    record = new_batch_record("KAYUMANGGI", "INC-7", 100, "2026-01-01")
    record.update(changes)
    return record


def test_full_batch_selection_and_pending_creation_survive_restart(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    record = batch()
    saved = db.save_local_batch(record, "station", "Worker")
    db.remember_batch_selection(saved["batch_id"], "Worker", 20)
    restarted = LocalDatabaseManager(db.db_path)
    assert restarted.get_local_batch(record["batch_id"])["initial_egg_count"] == 100
    assert restarted.get_batch_preferences()["egg_count"] == 20
    assert restarted.get_batch_preferences()["batch_id"] == record["batch_id"]
    assert restarted.get_pending_batch_count() == 1
    assert len(restarted.list_available_batches()) == 1
    assert restarted.save_local_batch(record, "station", "Worker")["batch_id"] == record["batch_id"]
    with pytest.raises(ValueError, match="different details"):
        restarted.save_local_batch({**record, "initial_egg_count": 99}, "station", "Worker")


@pytest.mark.parametrize("breed,count,date", [
    ("PEKIN", "100", "2026-01-01"), ("KHAKI_CAMPBELL", "100", "2026-01-01"),
    ("KHAKI", "0", "2026-01-01"), ("ITIM", "1.5", "2026-01-01"),
    ("ITIM", True, "2026-01-01"), ("KAYUMANGGI", "10", ""),
    ("KAYUMANGGI", "10", "2999-01-01"),
])
def test_no_fabricated_inventory_date_or_unsupported_breed(breed, count, date):
    with pytest.raises(ValueError):
        new_batch_record(breed, "INC-7", count, date)


def test_cache_offline_and_legacy_metadata_completion_preserve_scan_ids(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    session = local_run(db, "LEGACY-BATCH")
    scan = db.get_uncommitted_scans()[0]
    assert db.list_available_batches()[0]["needs_details"]
    legacy = batch(batch_id="LEGACY-BATCH", batch_code="LEGACY-BATCH")
    db.save_local_batch(legacy, "station", "Worker")
    assert db.get_uncommitted_scans()[0] == scan
    assert db.get_session_stats(session)["batch_id"] == "LEGACY-BATCH"
    office = batch(batch_code="Office batch")
    db.cache_batches([office])
    db.cache_batches([{**legacy, "initial_egg_count": 999}])  # Remote refresh cannot overwrite a pending local record.
    assert db.get_local_batch("LEGACY-BATCH")["initial_egg_count"] == 100
    monkeypatch.setattr("src.sync.sync_worker.requests.get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError()))
    records = BackgroundSyncWorker(db, api_key="test").fetch_active_batches()
    assert {r["batch_id"] for r in records} == {legacy["batch_id"], office["batch_id"]}
    assert db.get_pending_batch_count() == 1


@pytest.mark.parametrize("failure", ["lost", "wrong_id", "wrong_count", "conflict", "offline"])
def test_registration_retry_is_durable_and_precedes_session_scans(tmp_path, monkeypatch, failure):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    record = batch()
    db.save_local_batch(record, "station", "Worker")
    session_id = local_run(db, record["batch_id"])
    backend = Backend(db, monkeypatch)
    original = backend.post
    phase, created, calls = {"failure": failure}, {}, []
    def post(url, **kwargs):
        calls.append(url)
        if not url.endswith("/batches/register"):
            assert record["batch_id"] in created and db.get_local_batch(record["batch_id"])["synced_at"]
            return original(url, **kwargs)
        if phase["failure"] == "offline":
            raise requests.ConnectionError()
        if phase["failure"] == "conflict":
            return response({}, 409)
        created.setdefault(kwargs["json"]["batch_id"], deepcopy(kwargs["json"]))
        if phase["failure"] == "lost":
            raise requests.ConnectionError("committed response lost")
        body = deepcopy(created[record["batch_id"]])
        if phase["failure"] == "wrong_id":
            body["batch_id"] = str(uuid4())
        if phase["failure"] == "wrong_count":
            body["initial_egg_count"] = True
        return response(body)
    monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
    worker = BackgroundSyncWorker(db, api_key="test")
    worker._perform_sync()
    assert db.get_pending_batch_count() == 1 and db.get_unsynced_count() == 1
    assert not backend.sessions and worker.last_error
    phase["failure"] = None
    BackgroundSyncWorker(LocalDatabaseManager(db.db_path), api_key="test")._perform_sync()
    assert len(created) == 1 and db.get_pending_batch_count() == db.get_unsynced_count() == 0
    assert db.get_session_stats(session_id)["end_synced_at"]
    assert calls.index(next(url for url in calls if url.endswith("/batches/register"))) < calls.index(next(url for url in calls if url.endswith("/sessions")))


def test_creation_without_scans_is_synced_and_one_conflict_cannot_starve_another(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    bad, good = batch(), batch()
    for record in (bad, good):
        db.save_local_batch(record, "station", "Worker")
    monkeypatch.setattr("src.sync.sync_worker.requests.post", lambda url, **k:
        response(k["json"], 409 if k["json"]["batch_id"] == bad["batch_id"] else 200))
    worker = BackgroundSyncWorker(db, api_key="test")
    worker._perform_sync()
    assert db.get_local_batch(good["batch_id"])["synced_at"]
    assert not db.get_local_batch(bad["batch_id"])["synced_at"]
    assert "conflicts" in worker.last_error and db.get_pending_batch_count() == 1


def test_storage_connections_close_and_failed_transactions_roll_back(tmp_path):
    import sqlite3
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    with pytest.raises(RuntimeError):
        with db._get_connection() as conn:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            conn.execute("INSERT INTO machine_journal VALUES ('rollback', '{}')")
            raise RuntimeError("abort before commit")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")
    assert db.load_machine_state("rollback") is None


def test_concurrent_station_processes_preserve_wal_integrity(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import subprocess
    import time
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    code = """import sys, uuid
sys.path.insert(0, sys.argv[1])
from src.db.local_db import LocalDatabaseManager
db = LocalDatabaseManager(sys.argv[2])
for _ in range(25):
    db.create_session(str(uuid.uuid4()), 'BATCH', 'DEVICE', 'DAY_10', 'Worker')
"""
    def writer():
        return subprocess.run([sys.executable, "-c", code, str(Path(__file__).resolve().parents[1]), db.db_path],
                              capture_output=True, text=True, timeout=30)
    with ThreadPoolExecutor(max_workers=2) as pool:
        writers = [pool.submit(writer) for _ in range(2)]
        while not all(future.done() for future in writers):
            db.get_pending_batch_count()
            time.sleep(.005)
        for future in writers:
            result = future.result()
            assert result.returncode == 0, result.stderr
    with db._get_connection() as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM local_sessions").fetchone()[0] == 50


def test_batch_network_registration_does_not_hold_the_storage_lock(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    db.save_local_batch(batch(), "station", "Worker")
    with ThreadPoolExecutor(max_workers=1) as pool:
        def post(url, **kwargs):
            assert pool.submit(db.get_pending_batch_count).result(timeout=2) == 1
            return response(kwargs["json"])
        monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
        worker = BackgroundSyncWorker(db, api_key="test")
        worker._sync_batches()
    assert not worker.last_error and db.get_pending_batch_count() == 0
