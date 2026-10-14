"""Status caching must preserve operator lock and recovery transitions."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ui.app import OvaLensOperatorApp


def controls():
    app = SimpleNamespace(current_session_id=None, station=None, is_auto_cycle_running=False,
                          _scan_busy=False, _stopping=False, _closing=False,
                          _pending_finalization_id=None, _finalization_failed=False,
                          inference_worker=SimpleNamespace(busy=False), _diagnostics_complete=False)
    for name in ('session_btn', 'scan_btn', 'cancel_btn', 'hud_cancel_btn', 'eject_btn',
                 'batch_setup_btn', 'settings_btn'):
        setattr(app, name, Mock())
    return app


def test_unchanged_controls_skip_tk_but_inference_busy_and_recovery_refresh():
    app = controls()
    refresh = lambda: OvaLensOperatorApp._set_session_active_state(app, False)
    refresh()
    first = app.scan_btn.configure.call_count
    refresh()
    assert app.scan_btn.configure.call_count == first
    app.inference_worker.busy = True
    refresh()
    assert app.scan_btn.configure.call_args.kwargs['state'] == 'disabled'
    app.inference_worker.busy = False
    refresh()
    assert app.scan_btn.configure.call_args.kwargs['state'] == 'normal'
    app._finalization_failed = True
    refresh()
    assert app.scan_btn.configure.call_args.kwargs['state'] == 'disabled'
    assert app.cancel_btn.configure.call_args.kwargs['text'] == 'Retry Finalization'
    app._finalization_failed = False
    refresh()
    assert app.settings_btn.configure.call_args.kwargs['state'] == 'normal'


def test_session_identity_and_diagnostic_completion_invalidate_controls():
    app = controls()
    refresh = lambda: OvaLensOperatorApp._set_session_active_state(app, False)
    refresh()
    app._diagnostics_complete = True
    refresh()
    assert app.scan_btn.configure.call_args.kwargs['state'] == 'disabled'
    app.current_session_id = 'unfinished'
    refresh()
    assert app.settings_btn.configure.call_args.kwargs['state'] == 'disabled'
    app.station = SimpleNamespace(cycle=SimpleNamespace(session_id='unfinished'))
    app.is_auto_cycle_running = True
    refresh()
    assert app.session_btn.configure.call_args.kwargs['state'] == 'normal'


def test_setup_locks_scanning_and_start_until_preparation_completes():
    app = controls()
    app.station = SimpleNamespace(cycle=None, calibrated=False, boards=None)
    refresh = lambda: OvaLensOperatorApp._set_session_active_state(app, False)
    refresh()
    assert app.session_btn.configure.call_args.kwargs['state'] == 'disabled'
    app._setup_busy = True
    refresh()
    for button in (app.settings_btn, app.batch_setup_btn, app.scan_btn, app.session_btn):
        assert button.configure.call_args.kwargs['state'] == 'disabled'
    app._setup_busy = False
    app.station.calibrated = True
    app._station_prepared = app._batch_record_ready = True
    app.setup_inspected = SimpleNamespace(get=lambda: True)
    refresh()
    assert app.session_btn.configure.call_args.kwargs['state'] == 'normal'


def test_review_message_and_color_are_never_suppressed_by_hud_cache():
    app = SimpleNamespace(cycle_hud=Mock(), cycle_status_dot=Mock(), cycle_status_label=Mock())
    refresh = lambda message, color: OvaLensOperatorApp._update_cycle_hud(app, '●', color, message)
    refresh('Ready', '#FFFFFF')
    refresh('Ready', '#FFFFFF')
    assert app.cycle_status_label.configure.call_count == 1
    refresh('Storage failure; inspect station', '#FBBF24')
    assert app.cycle_status_label.configure.call_count == 2
    assert app.cycle_status_label.configure.call_args.kwargs['text'] == 'Storage failure; inspect station'


def test_review_choices_follow_cycle_state_and_hide_after_resolution():
    cycle = SimpleNamespace(session_id='cycle', latest_result=None,
                            status={'state': 'MANUAL_REVIEW', 'holder': 3, 'reason': 'Class disagreement'})
    app = SimpleNamespace(station=SimpleNamespace(boards=None, cycle=cycle),
                          camera=SimpleNamespace(last_error=None, is_running=True),
                          current_session_id=None, station_status=Mock(), review_row=Mock(),
                          review_buttons=[Mock(), Mock(), Mock()], _update_cycle_hud=Mock(), _log=Mock())
    OvaLensOperatorApp._poll_station(app)
    app.review_row.pack.assert_called_once()
    for button in app.review_buttons:
        assert button.configure.call_args.kwargs['state'] == 'normal'
    OvaLensOperatorApp._poll_station(app)
    app.review_row.pack.assert_called_once()
    cycle.status = {'state': 'INDEXING', 'holder': 3, 'reason': ''}
    OvaLensOperatorApp._poll_station(app)
    app.review_row.pack_forget.assert_called_once()
    for button in app.review_buttons:
        assert button.configure.call_args.kwargs['state'] == 'disabled'
