"""TASK-NEW-EDGE-EASYFLOW-01: one-action setup, cancellation and batch totals."""
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import queue
import threading

import pytest

from test_operator_flow import operator
from test_station_setup import station_fixture, commands
from src.core.operator_cues import cycle_cue


class Flag:
    def __init__(self, value=True):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def simple_operator(tmp_path):
    app = operator(tmp_path)
    app.setup_inspected = Flag()
    app.setup_notice = Mock()
    app.iot_status_badge = Mock()
    app._ui_events = queue.Queue()
    app._setup_busy = app._batch_complete = app.simulation = False
    app._setup_request = app._automatic_complete_cycle = None
    app._batch_record_ready = True
    app.refresh_readiness = Mock()
    app.station = SimpleNamespace(active=False, cycle=None, halt=Mock(),
        prepare_for_sorting=Mock(return_value="Ready"),
        start_cycle=Mock(return_value=SimpleNamespace(session_id="cycle")))
    app.station.settings = SimpleNamespace(rig_profile="three_v3")
    readiness = SimpleNamespace(ready=False, reason="Prepare station", prepare=Mock(), start=Mock())
    def prepare(*args, **kwargs):
        app.station.prepare_for_sorting(*args)
        readiness.ready = True
    readiness.prepare.side_effect = prepare
    readiness.start.side_effect = lambda batch, target, operator, cancel: app.station.start_cycle(batch, target, operator)
    app.station.readiness = readiness
    app._set_session_active_state = Mock()
    app.open_batch_setup_dialog = Mock()
    from src.ui.app import OvaLensOperatorApp
    for name in ("toggle_auto_session", "_activate_cycle", "_finalize_automatic_batch", "trigger_manual_eject", "prepare_station", "_submit_station_request"):
        setattr(app, name, MethodType(getattr(OvaLensOperatorApp, name), app))
    return app


def test_prepare_finishes_without_starting_then_final_start_reuses_it(tmp_path):
    app = simple_operator(tmp_path)
    app.toggle_auto_session()
    assert not app._jobs.work
    app.prepare_station()
    app.prepare_station()
    assert app._setup_busy and len(app._jobs.work) == 1
    app.station.start_cycle.assert_not_called()
    app._jobs.finish()
    assert not app._setup_busy and not app.is_auto_cycle_running
    app.station.prepare_for_sorting.assert_called_once()
    app.toggle_auto_session()
    app.toggle_auto_session()
    app._jobs.finish()
    assert app.is_auto_cycle_running
    app.station.prepare_for_sorting.assert_called_once()
    app.station.start_cycle.assert_called_once_with(app.current_batch_id, app.target_egg_count, app.operator_name)
    assert app.current_session_id == "cycle"


def test_unknown_batch_prompts_for_details_before_hardware_setup(tmp_path):
    app = simple_operator(tmp_path)
    app._batch_record_ready = False
    app.toggle_auto_session()
    app.open_batch_setup_dialog.assert_called_once()
    app.station.prepare_for_sorting.assert_not_called()
    app.station.start_cycle.assert_not_called()
    assert not app._jobs.work


@pytest.mark.parametrize("worker_finished", [False, True])
def test_stop_during_setup_never_starts_a_late_result(tmp_path, worker_finished):
    app = simple_operator(tmp_path)
    app.prepare_station()
    request = app._setup_request
    work, success, failure = app._jobs.work.pop(0)
    result = work() if worker_finished else None
    app.trigger_manual_eject()
    assert request["cancel"].is_set()
    success(result)
    assert not app.is_auto_cycle_running and app.current_session_id is None
    app.station.start_cycle.assert_not_called()
    app.station.halt.assert_called()
    while app._jobs.work:
        app._jobs.finish()


@pytest.mark.parametrize("invalid", ["unchecked", "operator"])
def test_setup_validation_runs_before_hardware(tmp_path, invalid):
    app = simple_operator(tmp_path)
    if invalid == "unchecked":
        app.setup_inspected.set(False)
    else:
        app.operator_name = ""
    app.prepare_station()
    assert not app._jobs.work
    app.station.prepare_for_sorting.assert_not_called()


def test_setup_failure_does_not_start_and_can_retry_after_inspection(tmp_path):
    app = simple_operator(tmp_path)
    app.station.prepare_for_sorting.side_effect = RuntimeError("Camera unavailable")
    app.prepare_station()
    app._jobs.finish()
    assert not app._setup_busy and not app.is_auto_cycle_running
    app.station.start_cycle.assert_not_called()
    app.setup_inspected.set(True)
    app.station.prepare_for_sorting.side_effect = None
    app.prepare_station()
    app._jobs.finish()
    assert not app.is_auto_cycle_running
    app.toggle_auto_session()
    app._jobs.finish()
    assert app.is_auto_cycle_running


def test_saved_dual_profile_requires_advanced_preparation(tmp_path):
    app = simple_operator(tmp_path)
    app.station.settings = SimpleNamespace(rig_profile="dual_v2")
    app.station.calibrated = False
    app.toggle_auto_session()
    app.station.start_cycle.assert_not_called()
    app.station.calibrated = True
    app.toggle_auto_session()
    app.station.start_cycle.assert_called_once()
    app.station.prepare_for_sorting.assert_not_called()


def test_preview_start_failure_is_recoverable(tmp_path):
    app = simple_operator(tmp_path)
    app.camera.start.side_effect = RuntimeError("Camera unavailable")
    from src.ui.app import OvaLensOperatorApp
    OvaLensOperatorApp._start_preview(app)
    assert app._operator_state.value == "ERROR"
    app.station.start_cycle.assert_not_called()


def completed_cycle(app):
    app.db.create_session("cycle", app.current_batch_id, "station", "DAY_10", "Tester")
    app.db.complete_session("cycle")
    app.current_session_id = "cycle"
    app.is_session_active = True
    cycle = SimpleNamespace(session_id="cycle", active=False, status={"state": "COMPLETE"}, count=0, routed=0)
    app.station.cycle = cycle
    return cycle


def test_completed_batch_finalizes_inline_without_stopping_preview(tmp_path):
    app = simple_operator(tmp_path)
    app._finalize_automatic_batch(completed_cycle(app))
    app._jobs.finish()
    assert app._batch_complete and app.current_session_id is None
    assert not app._stopping and not app.is_session_active
    app.camera.stop.assert_not_called()
    app.open_batch_completion_modal.assert_not_called()
    app.toggle_auto_session()
    app.open_batch_setup_dialog.assert_called_once()


def test_failed_totals_keep_identity_and_can_retry(tmp_path, monkeypatch):
    app = simple_operator(tmp_path)
    cycle = completed_cycle(app)
    read = app.db.get_session_stats
    monkeypatch.setattr(app.db, "get_session_stats", Mock(side_effect=OSError("disk unavailable")))
    app._finalize_automatic_batch(cycle)
    app._jobs.finish()
    assert app._finalization_failed and app.current_session_id == "cycle"
    monkeypatch.setattr(app.db, "get_session_stats", read)
    app.stop_or_cancel_session()
    app._jobs.finish()
    assert app._batch_complete and app.current_session_id is None


def test_combined_setup_preserves_calibration_and_reuses_healthy_connections(tmp_path, monkeypatch):
    station, opened, wires, _ = station_fixture(tmp_path, monkeypatch)
    station.settings.camera.exposure = -7
    station.settings.calibration.hold_ms = 800
    station.settings.calibration.settle_ms = 1900
    station.settings.calibration.sorter_steps = 900
    try:
        station.prepare_for_sorting(True, threading.Event())
        saved = station.store.load()
        assert saved.camera.exposure == -7
        assert saved.calibration.hold_ms == 800 and saved.calibration.sorter_steps == 900
        assert saved.calibration.settle_ms == 1900
        assert saved.camera.index == 0 and saved.camera.identity
        initial = len(opened)
        station.prepare_for_sorting(True, threading.Event())
        assert len(opened) == initial and station.calibrated
        assert not any(c.startswith(("ADVANCE:", "SORT:", "RESUME")) for c in commands(wires))
    finally:
        station.stop()


@pytest.mark.parametrize("stage", ["unchecked", "queued", "camera", "discovery", "preparation"])
def test_combined_setup_cancellation_blocks_further_preparation(tmp_path, monkeypatch, stage):
    station, opened, wires, applied = station_fixture(tmp_path, monkeypatch)
    cancel = threading.Event()
    if stage == "queued":
        cancel.set()
    if stage == "camera":
        original = station.apply
        def apply(*args, **kwargs):
            original(*args, **kwargs)
            station.halt()
        monkeypatch.setattr(station, "apply", apply)
    if stage == "discovery":
        def discover(**kwargs):
            station.halt()
            return dict(zip(("CONVEYOR", "EGG_CONTROLLER", "LIGHT_CONTROLLER"), ("COM5", "COM7", "COM9")))
        monkeypatch.setattr("src.core.station.discover_boards", discover)
    if stage == "preparation":
        monkeypatch.setattr(station, "prepare_empty_conveyor", lambda *args, **kwargs: station.halt())
    try:
        with pytest.raises(RuntimeError):
            station.prepare_for_sorting(stage != "unchecked", cancel)
        assert not station.calibrated
        if stage in {"unchecked", "queued"}:
            assert not opened and not applied
        assert not any(c.startswith(("ADVANCE:", "SORT:", "RESUME")) for c in commands(wires))
    finally:
        station.stop()


def test_only_clear_searching_state_invites_feeding():
    for state in ("SEARCHING", "LIGHTING", "STABILIZING", "CLASSIFYING", "SAVING", "ROUTING", "DISPLAYING", "INDEXING", "MANUAL_REVIEW", "RECOVERY_REQUIRED", "COMPLETE", "UNKNOWN"):
        title, detail, tone = cycle_cue({"state": state})
        assert title and detail and tone
        assert (title == "Feed next egg") == (state == "SEARCHING")


def test_external_stop_during_presets_prevents_gate_reset(tmp_path, monkeypatch):
    station, _, wires, _ = station_fixture(tmp_path, monkeypatch)
    cancel = threading.Event()
    try:
        station.use_defaults_and_detect()
        original = station.boards.conveyor.command
        def command(text, timeout=3):
            result = original(text, timeout)
            if text.startswith("SPEED:"):
                cancel.set()
            return result
        monkeypatch.setattr(station.boards.conveyor, "command", command)
        with pytest.raises(RuntimeError, match="Setup stopped"):
            station.prepare_for_sorting(True, cancel)
        assert "RESET" not in commands(wires) and not station.calibrated
    finally:
        station.stop()
