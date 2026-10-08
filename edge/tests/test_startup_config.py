"""TASK-NEW-EDGE-START-01: build the real startup UI without hardware access."""
from pathlib import Path
import sys
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ui.startup_config import StartupConfigWindow  # noqa: E402
from src.ui.app import OvaLensOperatorApp  # noqa: E402


@pytest.fixture
def hidden_ui(monkeypatch):
    original = tk.Tk.__init__

    def hidden_init(self, *args, **kwargs):
        try:
            original(self, *args, **kwargs)
        except tk.TclError as exc:
            pytest.skip(f"Tk display/runtime unavailable: {exc}")
        tk.Tk.withdraw(self)

    monkeypatch.setattr(tk.Tk, "__init__", hidden_init)
    monkeypatch.setattr("serial.tools.list_ports.comports", lambda: [])


def test_startup_window_builds_and_cancels_without_hardware(hidden_ui):
    # A TclError from a widget (such as an unsupported color) must fail,
    # rather than be mistaken for an unavailable display and skipped.
    window = StartupConfigWindow()
    try:
        window.update_idletasks()
        assert window.result is None
        assert not hasattr(window, "_port_var")  # Board selection lives in station settings.
        window._on_cancel()
    finally:
        try:
            window.destroy()
        except tk.TclError:
            pass


def test_operator_window_and_shutdown_without_hardware(hidden_ui):
    camera = SimpleNamespace(is_running=False, current_fps=0.0, last_error=None,
                             is_mock_mode=False, stop=Mock())
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    db = Mock()
    db.get_unsynced_count.return_value = 0
    db.get_distinct_batches.return_value = []
    db.get_scans_by_batch.return_value = []
    app = OvaLensOperatorApp(camera, Mock(), Mock(), db, sync)
    assert app.is_fullscreen is True
    assert "Windowed" in app.kiosk_btn.cget("text")

    # Verify fullscreen toggling behavior
    app.toggle_fullscreen()
    assert app.is_fullscreen is False
    assert "Kiosk" in app.kiosk_btn.cget("text")
    app.toggle_fullscreen()
    assert app.is_fullscreen is True
    assert "Windowed" in app.kiosk_btn.cget("text")

    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    app.after(50, app.open_scan_history_modal)
    app.after(300, app.shutdown)
    app.mainloop()
    assert not errors
    assert app._jobs.closed.is_set()
    camera.stop.assert_called()
    sync.stop.assert_called_once()


def test_live_preview_does_not_submit_background_inference(hidden_ui):
    import time
    import numpy as np
    from src.core.camera import CameraFrame
    from src.core.inference_worker import InferenceWorker
    frame = CameraFrame(1, time.monotonic(), 0, np.zeros((120, 160, 3), dtype=np.uint8))
    camera = SimpleNamespace(is_running=True, current_fps=30., last_error=None,
        is_mock_mode=False, stop=Mock(), snapshot=Mock(return_value=frame))
    engine = SimpleNamespace(predict=Mock())
    worker = InferenceWorker(engine)
    worker.start()
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    db = Mock()
    db.get_unsynced_count.return_value = 0
    app = OvaLensOperatorApp(camera, engine, None, db, sync, fullscreen=False, inference_worker=worker)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    app.after(200, app.shutdown)
    app.mainloop()
    assert not errors
    assert camera.snapshot.call_count > 1
    engine.predict.assert_not_called()
    assert not hasattr(app, "realtime_detector")


def test_startup_window_confirms_fullscreen_config(hidden_ui):
    window = StartupConfigWindow()
    try:
        window.update_idletasks()
        window._operator_entry.insert(0, "Pedro Penduko")
        window._on_start()
        assert window.result is not None
        assert window.result.get("fullscreen") is True
    finally:
        try:
            window.destroy()
        except tk.TclError:
            pass


def test_station_settings_builds_without_camera_or_board_access(hidden_ui, tmp_path):
    from src.core.settings import EdgeSettings, SettingsStore
    from src.ui.station_settings import StationSettingsWindow
    station = SimpleNamespace(settings=EdgeSettings(), settings_error="", boards=None, cycle=None,
                              store=SettingsStore(tmp_path / "defaults.json"), active=False,
                              calibrated=False,
                              halt=Mock(), stop=Mock())
    camera = SimpleNamespace(is_running=False, current_fps=0., last_error=None, is_mock_mode=False, stop=Mock())
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    db = Mock()
    db.get_unsynced_count.return_value = 0
    app = OvaLensOperatorApp(camera, Mock(), Mock(), db, sync, fullscreen=False, station=station)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    window = StationSettingsWindow(app)
    window.withdraw()
    window.update_idletasks()
    from src.ui.theme import FUTheme
    assert window.entries["detection.iou"].cget("font")[0] == FUTheme.FONT_FAMILY
    assert window._values().snapshot() == station.settings.snapshot()
    assert "camera.auto_exposure" in window.entries
    assert "detection.iou" in window.entries
    assert "calibration.ir_offset_steps" in window.entries
    assert "conveyor_port" in window.entries and "servo_port" in window.entries
    assert "light_port" in window.entries
    assert window.profile.get() == "Two-board indexed rig"
    window.profile.set("Three-board candling rig")
    window._rig_defaults()
    three = window._values()
    assert three.rig_profile == "three_v3" and three.camera.index == 0
    assert three.calibration.fertile_angle == 180 and three.calibration.buffer_drain == 6
    assert three.calibration.settle_ms == 700 and three.calibration.hold_ms == 300
    assert not station.halt.called
    window._close()
    app.after(50, app.shutdown)
    app.mainloop()
    assert not errors


def test_minimum_window_keeps_stop_and_session_controls_visible(hidden_ui):
    import queue
    camera = SimpleNamespace(is_running=False, current_fps=0., last_error=None,
                             is_mock_mode=False, stop=Mock())
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    db = Mock()
    db.get_unsynced_count.return_value = 0
    worker = SimpleNamespace(busy=False, result_queue=queue.Queue(), stop=Mock())
    app = OvaLensOperatorApp(camera, Mock(), None, db, sync, fullscreen=False,
                             inference_worker=worker)
    try:
        app.geometry("1024x720")
        app.deiconify()
        app.update()
        app.current_session_id = "inspection"
        app.is_auto_cycle_running = True
        app._set_session_active_state(True)
        app.review_row.pack(fill="x", padx=12, pady=(0, 8))
        app.update_idletasks()
        assert not app.cancel_btn.winfo_ismapped()  # STOP handles automatic sorting.
        for button in (app.eject_btn, app.session_btn, app.settings_btn,
                       app.kiosk_btn, *app.review_buttons):
            assert button.winfo_ismapped()
            assert button.winfo_rootx() >= app.winfo_rootx()
            assert button.winfo_rootx() + button.winfo_width() <= app.winfo_rootx() + app.winfo_width()
        assert app.video_container.winfo_height() > 200
        assert app.log_textbox.winfo_ismapped()
        assert app.log_textbox.winfo_height() >= 32
        # A stopped holder's reason owns the HUD; duplicate session controls
        # must not consume its width at the minimum supported resolution.
        app._update_cycle_hud("●", "#FBBF24", "MANUAL_REVIEW | Holder 3 | Conflicting IR and camera evidence")
        app.update_idletasks()
        assert app.cycle_status_label.winfo_width() >= 340
    finally:
        app.current_session_id = None
        app.is_auto_cycle_running = False
        app.shutdown()
        app.mainloop()


def test_simple_setup_main_screen_without_hardware(hidden_ui):
    import queue
    import threading
    import time
    entered, release = threading.Event(), threading.Event()
    cycle = SimpleNamespace(session_id="cycle", active=False, latest_result=None,
        status={"state": "SEARCHING", "holder": 1, "reason": "Gate clear"}, count=0, routed=0)
    station = SimpleNamespace(cycle=None, boards=None, calibrated=False, recovery=None,
        active=False, halt=Mock(), stop=Mock(), start_cycle=Mock(return_value=cycle))
    def prepare(inspected, cancel, progress):
        assert inspected
        entered.set()
        assert release.wait(3)
        assert not cancel.is_set()
        progress("Station ready")
        station.calibrated = True
        station.cycle = cycle
        return "Ready"
    station.prepare_for_sorting = Mock(side_effect=prepare)
    camera = SimpleNamespace(is_running=False, current_fps=0., last_error=None,
                             is_mock_mode=False, stop=Mock())
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    db = Mock()
    db.get_unsynced_count.return_value = 0
    worker = SimpleNamespace(busy=False, result_queue=queue.Queue(), stop=Mock())
    app = OvaLensOperatorApp(camera, Mock(), None, db, sync, fullscreen=False,
                             inference_worker=worker, station=station)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.deiconify()
        for width, height in ((1280, 860), (1024, 720)):
            app.geometry(f"{width}x{height}")
            app.update()
            app._set_session_active_state(False)
            app.update_idletasks()
            for control in (app.session_btn, app.setup_check, app.eject_btn, app.settings_btn):
                assert control.winfo_ismapped()
                assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
            assert app.video_container.winfo_height() > 200
            assert not app.scan_btn.winfo_ismapped()
            assert app.settings_btn.cget("text") == "Tools"
        assert app.session_btn.cget("state") == "disabled"
        app.setup_inspected.set(True)
        app._set_session_active_state(False)
        app.session_btn.invoke()
        assert entered.wait(1)
        assert app._setup_busy and app.session_btn.cget("text") == "Preparing..."
        assert app.eject_btn.cget("state") == "normal"
        release.set()
        deadline = time.monotonic() + 3
        while app._setup_busy and time.monotonic() < deadline:
            app.update()
            time.sleep(.005)
        assert not app._setup_busy and app.is_auto_cycle_running
        station.start_cycle.assert_called_once()
        app._poll_station()
        assert app.cycle_status_label.cget("text") == "Feed next egg"
        assert not app.setup_row.winfo_ismapped()
        assert not errors
    finally:
        release.set()
        app.current_session_id = None
        app.is_session_active = app.is_auto_cycle_running = False
        app.shutdown()
        app.mainloop()
