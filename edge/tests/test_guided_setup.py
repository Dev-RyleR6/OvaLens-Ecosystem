"""TASK-NEW-EDGE-GUIDED-SETUP-01: roster, attribution and safe setup transitions."""
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock
import sys
import threading
import time
from uuid import uuid4
import importlib.util

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from src.ui.app import OvaLensOperatorApp
from src.iot.dual_board import BoardLink
from operator_helpers import select_staff, STAFF_ID
from test_operator_flow import operator
from test_operation_safety import prediction
from test_easy_operator_flow import simple_operator
from test_session_sync import Backend
from test_startup_config import hidden_ui
from test_camera_preview_ui import preview_app
from test_live_camera_ui import pump
from test_station_setup import station_fixture


def staff(name="Worker", role="OPERATOR", identity=STAFF_ID):
    return {"user_id": identity, "full_name": name, "role": role}


def test_roster_reopen_selection_empty_refresh_and_invalid_refresh(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    assert db.get_operator_state()["downloaded_at"] is None
    records = [staff("N" * 128, "ADMIN"), staff("Same Name", "MANAGER", str(uuid4())),
               staff("Same Name", identity=str(uuid4()))]
    db.cache_operators(records)
    db.select_operator(STAFF_ID)
    before = db.get_operator_state()
    for bad in ({}, [staff(identity="not-a-uuid")], [staff(), staff()], [staff("N" * 129)]):
        with pytest.raises((ValueError, KeyError, TypeError)):
            db.cache_operators(bad)
        assert db.get_operator_state() == before
    db = LocalDatabaseManager(db.db_path)
    assert db.get_operator_state() == before
    db.cache_operators([])
    assert db.get_operator_state()["downloaded_at"]
    assert not db.get_operator(STAFF_ID)
    with pytest.raises(ValueError):
        db.select_operator(STAFF_ID)


def test_failed_network_refresh_preserves_cache_and_successful_empty_refresh_clears_it(tmp_path, monkeypatch):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    db.cache_operators([staff()])
    worker = BackgroundSyncWorker(db, api_key="test")
    before = db.get_operator_state()
    monkeypatch.setattr("src.sync.sync_worker.requests.get", Mock(side_effect=requests.ConnectionError("offline")))
    with pytest.raises(requests.ConnectionError):
        worker.fetch_operators()
    assert db.get_operator_state() == before
    monkeypatch.setattr("src.sync.sync_worker.requests.get", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: []))
    assert worker.fetch_operators()["operators"] == []


def test_recorded_operator_snapshot_survives_rename_removal_and_offline_replay(tmp_path, monkeypatch):
    app = operator(tmp_path)
    select_staff(app, "Original Name")
    app._process_scan_result(prediction())
    app._jobs.finish()
    identity = app.current_session_id
    app.db.complete_session(identity)
    app.db.cache_operators([staff("Renamed")])
    app.db.cache_operators([])
    backend = Backend(app.db, monkeypatch)
    backend.end_failure = "lost"
    for _ in range(2):
        BackgroundSyncWorker(LocalDatabaseManager(app.db.db_path), api_key="test")._perform_sync()
    assert backend.sessions[identity]["operator_id"] == STAFF_ID
    assert backend.sessions[identity]["operator_name"] == "Original Name"
    assert app.db.get_session_stats(identity)["end_synced_at"]


def test_missing_registered_operator_opens_setup_before_sorting_or_diagnostics(tmp_path):
    app = simple_operator(tmp_path)
    app.operator_id = None
    app.toggle_auto_session()
    app.open_batch_setup_dialog.assert_called_once()
    assert not app._jobs.work
    app.open_batch_setup_dialog.reset_mock()
    app.trigger_candling_scan()
    app.open_batch_setup_dialog.assert_called_once()
    assert not app._jobs.work


def test_refreshed_ineligible_operator_blocks_preparation_before_connecting(tmp_path):
    app = simple_operator(tmp_path)
    select_staff(app)
    app.db.cache_operators([])
    app.prepare_station()
    app._jobs.finish()
    app.station.prepare_for_sorting.assert_not_called()
    app.station.start_cycle.assert_not_called()
    assert "registered operator" in app.setup_notice.configure.call_args.kwargs["text"]


@pytest.mark.skipif(importlib.util.find_spec("src.iot.unified_board") is None,
                    reason="Unified hardware integration is not installed in this checkout")
def test_unified_preparation_uses_single_board_discovery_without_three_board_fallback(tmp_path, monkeypatch):
    station, _, _, _ = station_fixture(tmp_path, monkeypatch)
    station.settings.rig_profile = "unified_v4"
    station.apply = Mock()
    station.connect = Mock()
    station.prepare_empty_conveyor = Mock()
    station.store.save = Mock()
    unified = Mock(return_value="COM-U")
    three = Mock(side_effect=AssertionError("Wrong profile discovery"))
    monkeypatch.setattr("src.iot.unified_board.discover_unified_board", unified)
    monkeypatch.setattr("src.core.station.discover_boards", three)
    station.prepare_for_sorting(True, threading.Event())
    unified.assert_called_once()
    three.assert_not_called()
    assert station.settings.conveyor_port == "COM-U"


@pytest.mark.parametrize("reply", ["READY:CONVEYOR_V3:PROTOCOL=3", "READY:UNIFIED_V2:PROTOCOL=2"])
def test_unified_protocol_identity_mismatch_cannot_be_ready(reply):
    link = BoardLink("UNIFIED", "COM-U", protocol=3)
    link._receive(reply, time.monotonic())
    assert not link.snapshot().identified and "mismatch" in link.snapshot().error


def test_native_startup_setup_search_targets_staff_and_cancel_without_preparation(hidden_ui, tmp_path):
    from src.core.batches import new_batch_record
    app, _, _ = preview_app(tmp_path)
    app._startup_guided_setup = True
    for code, incubator, count in [("Batch-A", "North", 100), ("Batch-B", "South", 250)]:
        record = new_batch_record("KAYUMANGGI", incubator, count, "2026-01-01", batch_code=code)
        app.db.save_local_batch(record, app.device_id, "Legacy Name")
    try:
        app.deiconify()
        pump(app, lambda: hasattr(app, "_batch_setup_window") and app._batch_setup_window.loaded)
        window = app._batch_setup_window
        assert "Connect once" in window.operator_status.cget("text") or "Roster refresh failed" in window.operator_status.cget("text")
        window.apply()
        assert "registered operator" in window.notice.cget("text")
        state = app.db.get_operator_state()
        app.db.cache_operators([staff("Same Name"), staff("Same Name", identity=str(uuid4()))])
        window.refresh_operators(app.db.get_operator_state())
        assert len(window.operator_labels) == 2
        window.choose_operator(next(label for label, identity in window.operator_labels.items() if identity == STAFF_ID))
        window.search_text.set("South")
        assert len(window.labels) == 1
        window.choose(next(iter(window.labels)))
        assert window.target.get() == "250"
        for size in ("1024x720", "1280x860"):
            app.geometry(size)
            app.update_idletasks()
            assert window.save.winfo_rooty() + window.save.winfo_height() <= window.winfo_rooty() + window.winfo_height()
        window.cancel.invoke()
        pump(app, lambda: not window.winfo_exists())
        assert not app.is_auto_cycle_running and not app._setup_busy
    finally:
        app.shutdown()
        if app.winfo_exists():
            app.destroy()


@pytest.mark.parametrize("cancellation", ["stop", "cancel"])
def test_native_preparation_requires_inspection_and_stop_cancels_delayed_confirm(hidden_ui, tmp_path, cancellation):
    from src.core.batches import new_batch_record
    app, _, _ = preview_app(tmp_path)
    select_staff(app)
    record = new_batch_record("KAYUMANGGI", "INC", 100, "2026-01-01")
    app.db.save_local_batch(record, app.device_id, app.operator_name)
    app._apply_batch_selection(record, app.operator_name, 100)
    app.station.settings.rig_profile = "three_v3"
    try:
        app.deiconify()
        app.session_btn.invoke()
        dialog = app._preparation_window
        dialog.confirm_button.invoke()
        assert "Confirm the inspection" in dialog.notice.cget("text") and not app._setup_busy
        pending = []
        app._animate_modal_close = lambda window, on_close=None: pending.append(on_close)
        dialog.inspected.set(True)
        dialog.confirm_button.invoke()
        if cancellation == "stop":
            app.trigger_manual_eject()
        else:
            dialog.cancel_button.invoke()
        pending[0]()
        app.update()
        assert not app._setup_busy and not app.is_auto_cycle_running
        dialog.destroy()
    finally:
        app.shutdown()
        if app.winfo_exists():
            app.destroy()
