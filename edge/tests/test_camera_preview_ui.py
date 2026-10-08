"""Native preview camera controls exercised with fake camera/serial surfaces."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import queue
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.camera import CameraFrame
from src.core.settings import SettingsStore
from src.core.station import EdgeStation
from src.db.local_db import LocalDatabaseManager
from src.ui.app import OvaLensOperatorApp
from test_startup_config import hidden_ui


def preview_app(tmp_path):
    image = np.full((720, 1280, 3), 35, dtype=np.uint8)
    applied = []
    def apply(settings, **kwargs):
        applied.append((settings, kwargs))
        properties = {name: {"requested": getattr(settings, name), "actual": getattr(settings, name),
            "status": "rejected / unsupported" if name == "sharpness" else "verified readback"}
            for name in ("focus", "autofocus", "brightness", "sharpness")}
        camera.property_report = properties
        return {"identity": "opencv:0:DSHOW", "properties": properties}
    camera = SimpleNamespace(is_running=True, current_fps=30., last_error=None, is_mock_mode=False,
        identity="opencv:0:DSHOW", exposure_modes={"On": 1., "Off": 0.}, property_report={},
        settings_revision=0, snapshot=lambda **kwargs: CameraFrame(1, time.monotonic(), 0, image),
        apply_settings=apply, stop=Mock())
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    worker = SimpleNamespace(busy=False, result_queue=queue.Queue(), stop=Mock(), submit=Mock())
    station = EdgeStation(camera, worker, db, "preview", SettingsStore(tmp_path / "settings.json"))
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    app = OvaLensOperatorApp(camera, Mock(), None, db, sync, inference_worker=worker,
                            fullscreen=False, station=station)
    return app, camera, applied


def finish(app, panel):
    deadline = time.monotonic() + 3
    while panel.pending and time.monotonic() < deadline:
        app.update()
        time.sleep(.005)
    assert not panel.pending


def test_camera_controls_apply_save_restore_and_error_without_hardware(hidden_ui, tmp_path, monkeypatch):
    app, camera, applied = preview_app(tmp_path)
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.deiconify()
        app.current_session_id = "busy"
        app.open_camera_controls()
        assert app._camera_panel is None
        app.current_session_id = None
        app.open_camera_controls()
        panel = app._camera_panel
        assert panel is not None and app.grab_current() is None
        for width, height in ((1280, 860), (1024, 720)):
            app.geometry(f"{width}x{height}")
            app.update()
            for control in (panel.done, *panel.controls[:3], app.eject_btn, app.camera_controls_btn):
                assert control.winfo_ismapped()
                assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
                assert control.winfo_rooty() + control.winfo_height() <= app.winfo_rooty() + app.winfo_height()
            assert app.video_label.winfo_ismapped()
            assert app.video_container.winfo_height() > 200
        assert app.session_btn.cget("state") == app.settings_btn.cget("state") == "disabled"
        app.trigger_candling_scan()
        app.inference_worker.submit.assert_not_called()
        panel.modes["autofocus"].set("Off")
        panel._manual_states()
        panel.entries["focus"].insert(0, "80")
        panel.entries["brightness"].insert(0, "10")
        panel.apply()
        finish(app, panel)
        assert len(applied) == 1 and applied[0][1] == {"controls_only": True}
        assert app.station.settings.camera.focus == 80
        assert not app.station.store.path.exists()
        assert "rejected / unsupported" in panel.readbacks["sharpness"].cget("text")
        panel.modes["autofocus"].set("On")
        panel._manual_states()
        assert panel.entries["focus"].cget("state") == "disabled"
        panel.apply(save=True)
        finish(app, panel)
        saved = app.station.store.load()
        assert saved.camera.autofocus == 1 and saved.camera.focus is None
        assert saved.camera.brightness == 10 and saved.calibration.settle_ms == 1500
        panel.entries["brightness"].delete(0, "end")
        panel.entries["brightness"].insert(0, "25")
        count = len(applied)
        panel.restore()
        finish(app, panel)
        assert len(applied) == count and panel.entries["brightness"].get() == "10.0"
        monkeypatch.setattr(app.station.store, "save", Mock(side_effect=OSError("disk full")))
        panel.apply(save=True)
        finish(app, panel)
        assert "disk full" in panel.notice.cget("text") and panel.done.cget("state") == "normal"
        panel.close()
        assert app._camera_panel is None
        camera.stop.assert_not_called()
        assert not errors
    finally:
        app.shutdown()
        app.mainloop()
