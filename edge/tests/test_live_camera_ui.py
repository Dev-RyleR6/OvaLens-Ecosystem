"""Live tuning coalesces edits without blocking the Tk thread or issuing motion."""
import threading
import time
from unittest.mock import Mock

from test_camera_preview_ui import preview_app, finish, hidden_ui

# Windows can spend several seconds processing initial Tk layout in a full run.
# Keep the simulated camera held until the test explicitly releases it, with a
# finite backstop if the test fails to reach its cleanup/release path.
SIMULATED_CAMERA_HOLD_TIMEOUT_S = 10


def pump(app, condition, timeout=3):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        app.update()
        time.sleep(.005)
    assert condition()


def test_live_edits_coalesce_stay_responsive_and_save_explicitly(hidden_ui, tmp_path):
    app, camera, applied = preview_app(tmp_path)
    original = camera.apply_settings
    entered, release = threading.Event(), threading.Event()
    def slow(settings, **kwargs):
        if not entered.is_set():
            entered.set()
            assert release.wait(SIMULATED_CAMERA_HOLD_TIMEOUT_S)
        return original(settings, **kwargs)
    camera.apply_settings = slow
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.deiconify()
        app.open_camera_controls()
        panel = app._camera_panel
        for value in range(20):
            panel._slider_changed("brightness", value)
        pump(app, entered.is_set)
        assert panel._live_busy and not panel.pending
        assert panel.entries["brightness"].cget("state") == "normal"
        assert panel.sliders["brightness"].cget("state") == "normal"
        for value in range(20, 100):
            panel._slider_changed("brightness", value)
        assert not applied
        release.set()
        pump(app, lambda: len(applied) == 2 and not panel._live_busy)
        assert [settings.brightness for settings, _ in applied] == [19, 99]
        assert all(options == {"controls_only": True, "live_preview": True} for _, options in applied)
        assert panel.entries["brightness"].get() == "99"  # Old completion never overwrites a newer edit.
        assert not app.station.store.path.exists()
        panel.modes["autofocus"].set("On")
        panel._mode_changed("On")
        assert panel.sliders["focus"].cget("state") == "disabled"
        pump(app, lambda: len(applied) == 3 and not panel._live_busy)
        assert applied[-1][0].autofocus == 1 and applied[-1][0].focus is None
        # A repeated focus-out event with identical values causes no extra request.
        panel._entry_changed("brightness")
        pump(app, lambda: panel._live_after is None)
        assert len(applied) == 3
        panel.apply(save=True)
        finish(app, panel)
        assert app.station.store.load().camera.brightness == 99
        panel.close()
        assert app._camera_panel is None and not errors
    finally:
        release.set()
        app.shutdown()
        app.mainloop()


def test_bad_live_value_retry_restore_stop_and_close_cancel_timers(hidden_ui, tmp_path):
    app, camera, applied = preview_app(tmp_path)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    original = camera.apply_settings
    try:
        app.deiconify()
        app.open_camera_controls()
        panel = app._camera_panel
        panel.entries["exposure"].insert(0, "-")
        panel._entry_changed("exposure")
        pump(app, lambda: panel._live_after is None)
        assert not applied and "must be a number" in panel.notice.cget("text")
        panel.entries["exposure"].delete(0, "end")
        camera.apply_settings = Mock(side_effect=RuntimeError("camera unavailable"))
        panel._slider_changed("brightness", 12)
        pump(app, lambda: camera.apply_settings.called and not panel._live_busy)
        assert "Live update failed" in panel.notice.cget("text")
        assert panel._live_after is None  # No automatic error retry loop.
        camera.apply_settings = original
        panel._slider_changed("brightness", 13)
        pump(app, lambda: len(applied) == 1 and not panel._live_busy)
        panel.apply(save=True)
        finish(app, panel)
        panel._slider_changed("brightness", 88)
        panel.restore()  # Supersedes the scheduled live update; fills form only.
        finish(app, panel)
        assert panel.entries["brightness"].get() == "13.0"
        assert len(applied) == 2 and panel._live_after is None
        panel._slider_changed("brightness", 90)
        app.trigger_manual_eject()
        assert panel._live_after is None and not panel._live_dirty
        assert len(applied) == 2
        panel._slider_changed("brightness", 91)
        panel.close()  # Finish the last valid edit even before the debounce fires.
        finish(app, panel)
        assert app._camera_panel is None and applied[-1][0].brightness == 91
        assert app.station.store.load().camera.brightness == 13
        assert not errors
    finally:
        app.shutdown()
        app.mainloop()


def test_switching_to_cradle_supersedes_scheduled_camera_edits(hidden_ui, tmp_path):
    app, _, applied = preview_app(tmp_path)
    try:
        app.open_camera_controls()
        panel = app._camera_panel
        panel._slider_changed("focus", 30)
        panel.section.set("Cradle")
        panel._section("Cradle")
        assert panel._live_after is None and not applied
        panel.close()
        assert app._camera_panel is None
    finally:
        app.shutdown()
        app.mainloop()


def test_save_and_done_wait_for_live_request_without_losing_latest_edit(hidden_ui, tmp_path):
    app, camera, applied = preview_app(tmp_path)
    original = camera.apply_settings
    entered, release = threading.Event(), threading.Event()
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    def slow(settings, **kwargs):
        if not entered.is_set():
            entered.set()
            assert release.wait(SIMULATED_CAMERA_HOLD_TIMEOUT_S)
        return original(settings, **kwargs)
    camera.apply_settings = slow
    try:
        app.deiconify()
        app.open_camera_controls()
        panel = app._camera_panel
        panel._slider_changed("brightness", 10)
        pump(app, entered.is_set)
        panel._slider_changed("brightness", 20)
        panel.apply(save=True)
        assert panel.pending and panel._live_after is None
        release.set()
        finish(app, panel)
        assert [settings.brightness for settings, _ in applied] == [10, 20]
        assert panel.entries["brightness"].get() == "20.0"
        assert app.station.store.load().camera.brightness == 20
        entered.clear()
        release.clear()
        panel._slider_changed("brightness", 30)
        pump(app, entered.is_set)
        panel._slider_changed("brightness", 31)
        panel.close()
        assert panel.pending and panel._live_after is None
        release.set()
        finish(app, panel)
        assert app._camera_panel is None
        assert [settings.brightness for settings, _ in applied] == [10, 20, 30, 31]
        assert app.station.store.load().camera.brightness == 20
        assert not errors
    finally:
        release.set()
        app.shutdown()
        app.mainloop()
