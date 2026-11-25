"""TASK-NEW-SESSION-THROUGHPUT-01: saved evidence, estimates and summary UI."""
from pathlib import Path
import sys
from types import MethodType
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.session_metrics import session_metrics, estimate_capacity
from src.db.local_db import LocalDatabaseManager
from src.ui.app import OvaLensOperatorApp
from test_operator_flow import operator
from test_easy_operator_flow import simple_operator, completed_cycle
from test_session_sync import Backend
from test_startup_config import hidden_ui


@pytest.mark.parametrize("end,count,seconds,rate", [
    ("2026-10-29T08:10:00+08:00", 120, 600, 12),
    ("2026-10-29T00:00:00.500+00:00", 1, .5, 120),
    ("2026-10-29T00:00:00+00:00", 1, 0, None),
    ("2026-10-29T00:10:00+00:00", 0, 600, 0),
    (None, 120, None, None), ("bad", 120, None, None),
    ("2026-10-28T23:59:00+00:00", 120, None, None),
    ("2026-10-29T00:10:00", 120, None, None),
])
def test_saved_metrics(end, count, seconds, rate):
    assert session_metrics("2026-10-29T00:00:00+00:00", end, count) == {
        "duration_seconds": seconds, "eggs_per_minute": rate}


@pytest.mark.parametrize("count,seconds,minutes,expected", [
    (120, 600, "30", 360), (1, 100, ".5", 0), (1, .5, ".1", 12),
    (0, 600, "10", None), (120, 0, "10", None), (120, None, "10", None),
    (120, -1, "10", None), (120, 600, "0", None), (120, 600, "-1", None),
    (120, 600, "nan", None), (120, 600, "inf", None), (120, 600, "", None),
    (120, 600, "1e309", None),
])
def test_estimate_inputs(count, seconds, minutes, expected):
    assert estimate_capacity(count, seconds, minutes) == expected


def saved_run(db, count=120):
    db.create_session("run", "BATCH", "DEVICE", "DAY_10", "Operator")
    with db._get_connection() as conn:
        conn.execute("UPDATE local_sessions SET started_at=? WHERE session_id='run'",
                     ("2026-10-29T00:00:00+00:00",))
        conn.commit()
    for sequence in range(count):
        db.record_scan(f"scan-{sequence}", "run", "BATCH", sequence + 1, "FERTILE", .9, 8, "ACCEPT", [])
    return db.complete_session("run", "2026-10-29T00:10:00+00:00")


def test_reopen_offline_replay_and_repeated_end_preserve_metrics(tmp_path, monkeypatch):
    from src.sync.sync_worker import BackgroundSyncWorker
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    before = saved_run(db)
    backend = Backend(db, monkeypatch)
    backend.end_failure = "lost"
    for _ in range(4):
        db = LocalDatabaseManager(db.db_path)
        BackgroundSyncWorker(db, api_key="test")._perform_sync()
    after = db.complete_session("run", "2026-10-30T00:10:00+00:00")
    assert len(backend.scans) == after["total_scanned"] == 120
    assert after["end_synced_at"]
    for key in ("ended_at", "duration_seconds", "eggs_per_minute"):
        assert after[key] == before[key]
    assert after["duration_seconds"] == 600 and after["eggs_per_minute"] == 12


@pytest.mark.parametrize("automatic", [False, True])
def test_summary_reads_saved_run_after_timer_cleared(tmp_path, automatic):
    app = simple_operator(tmp_path) if automatic else operator(tmp_path)
    if automatic:
        app._finalize_automatic_batch(completed_cycle(app))
    else:
        app.db.create_session("cycle", app.current_batch_id, "station", "DAY_10", "Tester")
        app.current_session_id = "cycle"
        app.is_session_active = True
        app.stop_or_cancel_session()
    app._jobs.finish()
    assert app._session_start_time is None and app.current_session_id is None
    expected = app.db.get_session_stats("cycle")
    app._show_session_summary = Mock()
    app.open_batch_completion_modal = MethodType(OvaLensOperatorApp.open_batch_completion_modal, app)
    app.open_batch_completion_modal()
    app._show_session_summary.assert_not_called()
    app._jobs.finish()
    app._show_session_summary.assert_called_once_with(expected)
    assert expected["duration_seconds"] is not None


def test_summary_discards_stale_background_load(tmp_path):
    app = operator(tmp_path)
    saved_run(app.db, 1)
    app._last_session_id = "run"
    app._show_session_summary = Mock()
    OvaLensOperatorApp.open_batch_completion_modal(app)
    app._operation_generation += 1
    app._jobs.finish()
    app._show_session_summary.assert_not_called()


def test_summary_ui_uses_persisted_counts_and_validates_input(hidden_ui, tmp_path):
    from test_camera_preview_ui import preview_app
    from test_live_camera_ui import pump

    app, _, _ = preview_app(tmp_path)
    saved_run(app.db)
    app._last_session_id = "run"
    app.total_count = 999  # Transient counters must not become report evidence.
    try:
        app.deiconify()
        app.open_batch_completion_modal()
        pump(app, lambda: hasattr(app, "_session_summary_window"))
        dialog = app._session_summary_window
        dialog._capacity_minutes.set("30")
        app.update_idletasks()
        assert "360 scans" in dialog._capacity_result.cget("text")
        for invalid in ("", "0", "-1", "nan", "inf"):
            dialog._capacity_minutes.set(invalid)
            assert "greater than zero" in dialog._capacity_result.cget("text")
        dialog._capacity_minutes.set(".5")
        assert "6 scans" in dialog._capacity_result.cget("text")
        assert dialog._capacity_entry.cget("height") == 44
        dialog.destroy()
    finally:
        app.shutdown()
        if app.winfo_exists():
            app.destroy()
