"""Native readiness, offline warning and explicit retry with simulated boards."""
from test_camera_preview_ui import preview_app
from test_startup_config import hidden_ui
from test_live_camera_ui import pump
from test_station_setup import station_fixture
from test_station_readiness import batch


def test_readiness_panel_tracks_prepare_fault_and_retry_without_hardware(hidden_ui, tmp_path, monkeypatch):
    app, camera, _ = preview_app(tmp_path)
    station, opened, wires, _ = station_fixture(tmp_path / "station", monkeypatch)
    station.camera = camera
    app.station, app.db = station, station.db
    batch_id = batch(station)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.deiconify()
        app._apply_batch_selection(station.db.get_local_batch(batch_id), "Worker", 10)
        pump(app, lambda: app.readiness_panel.winfo_ismapped())
        assert not opened
        for width, height in ((1024, 720), (1280, 860)):
            app.geometry(f"{width}x{height}")
            app.update()
            for control in (app.setup_check, app.prepare_btn, app.session_btn, app.eject_btn,
                            app.readiness_panel.retry, app.settings_btn):
                assert control.winfo_ismapped()
                assert control.winfo_rooty() + control.winfo_height() <= app.winfo_rooty() + app.winfo_height()
                assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
            assert app.video_container.winfo_height() > 200
        assert app.session_btn.cget("state") == "disabled"
        app.setup_inspected.set(True)
        app._set_session_active_state(False)
        app.prepare_btn.invoke()
        pump(app, lambda: not app._setup_busy)
        assert station.readiness.ready and not app.is_auto_cycle_running
        assert app.session_btn.cget("state") == "normal"
        app.refresh_readiness(force=True)
        assert "Offline" in app.readiness_panel.labels["sync"].cget("text")
        camera.last_error = "Camera unplugged"
        app.refresh_readiness(force=True)
        app._set_session_active_state(False)
        assert not app._station_prepared and not station.calibrated
        assert app.session_btn.cget("state") == "disabled"
        assert "Camera unplugged" in app.readiness_panel.labels["camera"].cget("text")
        camera.last_error = None
        app.refresh_readiness(force=True)
        assert not app._station_prepared
        app.setup_inspected.set(True)
        app.prepare_station()
        pump(app, lambda: not app._setup_busy)
        assert station.readiness.ready
        app.trigger_manual_eject()
        app.refresh_readiness(force=True)
        assert not station.readiness.ready
        assert not errors
    finally:
        app.shutdown()
        app.mainloop()
