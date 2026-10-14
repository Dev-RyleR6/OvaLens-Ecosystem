"""TASK-NEW-EDGE-READINESS-01: real storage and simulated controller checks."""
from types import SimpleNamespace
from unittest.mock import Mock
import threading

import pytest

from test_station_setup import station_fixture, commands
from src.core.batches import new_batch_record


def batch(station):
    record = new_batch_record("KAYUMANGGI", "INC-1", 20, "2026-01-01")
    station.db.save_local_batch(record, "station", "Worker")
    return record["batch_id"]


def test_startup_checks_do_not_open_ports_and_storage_probe_preserves_evidence(tmp_path, monkeypatch):
    s, opened, wires, _ = station_fixture(tmp_path, monkeypatch)
    s.db.save_machine_state("station", {"state": "RECOVERY_REQUIRED"})
    rows = s.readiness.software_checks()
    assert all(r.state == "Ready" for r in rows[:4])
    assert not opened and not commands(wires) and not s.calibrated
    assert s.db.load_machine_state("station") == {"state": "RECOVERY_REQUIRED"}
    assert not list((tmp_path / "local_scans").iterdir())
    with s.db._get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM machine_journal").fetchone()[0] == 1
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"


@pytest.mark.parametrize("failure", ["disk", "model", "warmup", "settings", "unchecked", "cancelled"])
def test_failed_software_or_inspection_never_connects_or_prepares(tmp_path, monkeypatch, failure):
    s, opened, wires, _ = station_fixture(tmp_path, monkeypatch)
    cancel = threading.Event()
    if failure == "disk":
        monkeypatch.setattr(s.db, "check_readiness", Mock(side_effect=OSError("Storage is read-only")))
    elif failure == "model":
        s.inference.engine.model_contract_verified = False
    elif failure == "warmup":
        s.inference.engine.warmup_complete = False
    elif failure == "settings":
        s.settings_error = "Settings are invalid"
    elif failure == "cancelled":
        cancel.set()
    with pytest.raises((RuntimeError, OSError)):
        s.readiness.prepare(failure != "unchecked", cancel)
    assert not opened and not commands(wires) and not s.readiness.ready


@pytest.mark.parametrize("change", ["camera", "revision", "settings", "disconnect", "reset", "sensor", "position", "angle", "lamp", "stop"])
def test_preparation_latches_invalid_until_explicitly_repeated(tmp_path, monkeypatch, change):
    s, _, _, _ = station_fixture(tmp_path, monkeypatch)
    try:
        s.readiness.prepare(True, threading.Event())
        assert s.readiness.ready
        if change == "camera":
            s.camera.last_error = "Unplugged"
        elif change == "revision":
            s.camera.settings_revision = 2
        elif change == "settings":
            s.settings.calibration.hold_ms += 10
        elif change == "disconnect":
            s.boards.conveyor.state.connected = False
        elif change == "reset":
            s.boards.failure = "Board reset"
        elif change == "sensor":
            s.boards.egg.state.telemetry["SENSOR"] = "1"
        elif change == "position":
            s.boards.conveyor.state.telemetry["POSITION"] = "50"
        elif change == "angle":
            s.boards.egg.state.telemetry["ANGLE"] = "180"
        elif change == "lamp":
            s.boards.light.state.telemetry["LIGHT"] = "1"
        else:
            s.halt()
        assert not s.readiness.ready and not s.calibrated
        s.camera.last_error = None
        s.boards.failure = ""
        s.boards.conveyor.state.connected = True
        s.boards.egg.state.telemetry["SENSOR"] = "0"
        assert not s.readiness.ready
    finally:
        s.stop()


def test_final_start_checks_status_and_storage_without_repeating_preparation(tmp_path, monkeypatch):
    s, opened, wires, _ = station_fixture(tmp_path, monkeypatch)
    try:
        batch_id = batch(s)
        s.readiness.prepare(True, threading.Event())
        before = [len(commands([wire])) for wire in wires]
        ports = len(opened)
        cycle = SimpleNamespace(session_id="test-cycle")
        start = Mock(return_value=cycle)
        monkeypatch.setattr(s, "start_cycle", start)
        assert s.readiness.start(batch_id, 10, "Worker", threading.Event()) is cycle
        assert [command for wire, count in zip(wires, before)
                for command in commands([wire])[count:]] == ["STATUS"] * 3
        assert len(opened) == ports
        start.assert_called_once_with(batch_id, 10, "Worker")
        assert not s.readiness.ready  # permission is single-use
    finally:
        s.stop()


@pytest.mark.parametrize("failure", ["storage", "unknown-batch", "conflict", "target", "cancelled"])
def test_final_start_failure_never_releases_conveyor(tmp_path, monkeypatch, failure):
    s, _, _, _ = station_fixture(tmp_path, monkeypatch)
    try:
        batch_id = batch(s)
        s.readiness.prepare(True, threading.Event())
        start = Mock()
        monkeypatch.setattr(s, "start_cycle", start)
        cancel = threading.Event()
        if failure == "storage":
            monkeypatch.setattr(s.db, "check_readiness", Mock(side_effect=OSError("Disk full")))
        elif failure == "unknown-batch":
            batch_id = "missing"
        elif failure == "conflict":
            s.db.mark_batch_attempt(batch_id, "Conflict", blocked=True)
        elif failure == "cancelled":
            cancel.set()
        with pytest.raises((RuntimeError, OSError)):
            s.readiness.start(batch_id, 100 if failure == "target" else 10, "Worker", cancel)
        start.assert_not_called()
        assert not s.calibrated
    finally:
        s.stop()


def test_low_disk_space_is_a_blocker(tmp_path, monkeypatch):
    s, _, _, _ = station_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr("shutil.disk_usage", lambda path: SimpleNamespace(free=255 * 1024 * 1024))
    with pytest.raises(OSError, match="256 MB"):
        s.db.check_readiness()


def test_corrected_settings_clear_startup_error_without_serial_access(tmp_path, monkeypatch):
    s, opened, _, _ = station_fixture(tmp_path, monkeypatch)
    s.settings_error = "Invalid saved settings"
    assert s.readiness.software_checks()[0].state == "Needs attention"
    s.apply(s.settings)
    assert not s.settings_error
    assert s.readiness.software_checks()[0].state == "Ready"
    assert not opened


def test_prepare_cannot_interrupt_an_active_sorting_cycle(tmp_path, monkeypatch):
    s, opened, _, _ = station_fixture(tmp_path, monkeypatch)
    s.cycle = SimpleNamespace(active=True, stop=Mock())
    with pytest.raises(RuntimeError, match="Stop sorting"):
        s.readiness.prepare(True, threading.Event())
    s.cycle.stop.assert_not_called()
    assert not opened


def test_recheck_storage_failure_revokes_preparation(tmp_path, monkeypatch):
    s, _, _, _ = station_fixture(tmp_path, monkeypatch)
    try:
        s.readiness.prepare(True, threading.Event())
        assert s.readiness.ready
        monkeypatch.setattr(s.db, "check_readiness", Mock(side_effect=OSError("Disk full")))
        rows = s.readiness.software_checks()
        assert next(r for r in rows if r.key == "storage").state == "Needs attention"
        assert not s.readiness.ready and "Disk full" in s.readiness.reason
    finally:
        s.stop()


def test_stop_during_final_status_check_prevents_cycle_start(tmp_path, monkeypatch):
    s, _, _, _ = station_fixture(tmp_path, monkeypatch)
    try:
        batch_id = batch(s)
        s.readiness.prepare(True, threading.Event())
        cancel = threading.Event()
        command = s.boards.conveyor.command
        def stop(text, *args, **kwargs):
            result = command(text, *args, **kwargs)
            cancel.set()
            return result
        monkeypatch.setattr(s.boards.conveyor, "command", stop)
        start = Mock()
        monkeypatch.setattr(s, "start_cycle", start)
        with pytest.raises(RuntimeError, match="Setup stopped"):
            s.readiness.start(batch_id, 10, "Worker", cancel)
        start.assert_not_called()
        assert not s.readiness.ready
    finally:
        s.stop()


def test_offline_batch_is_allowed_but_known_conflicts_survive_retries(tmp_path, monkeypatch):
    import requests
    from src.sync.sync_worker import BackgroundSyncWorker
    s, _, _, _ = station_fixture(tmp_path, monkeypatch)
    batch_id = batch(s)
    worker = BackgroundSyncWorker(s.db, api_key="test")
    post = Mock(side_effect=requests.ConnectionError("offline"))
    monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
    worker._sync_batches()
    assert s.db.get_local_batch(batch_id)["sync_error"]
    s.readiness.check_batch(batch_id, 10)
    post.side_effect = None
    post.return_value = SimpleNamespace(status_code=409)
    worker._sync_batches()
    assert s.db.get_local_batch(batch_id)["sync_blocked"] == 1
    with pytest.raises(RuntimeError, match="conflicts"):
        s.readiness.check_batch(batch_id, 10)
    post.side_effect = requests.ConnectionError("still offline")
    worker._sync_batches()
    s.db.mark_batch_attempt(batch_id)
    assert s.db.get_local_batch(batch_id)["sync_blocked"] == 1
    post.side_effect = None
    post.return_value = SimpleNamespace(status_code=200, json=lambda: s.db.get_local_batch(batch_id))
    worker._sync_batches()
    s.readiness.check_batch(batch_id, 10)
    assert s.db.get_local_batch(batch_id)["sync_blocked"] == 0
