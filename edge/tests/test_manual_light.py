"""Manual light ownership, STOP and operator controls, with fake serial devices."""
import threading
import time
from unittest.mock import Mock
from types import SimpleNamespace

import pytest

from test_camera_alignment import alignment_station
from test_camera_preview_ui import preview_app, hidden_ui
from test_live_camera_ui import pump


def light_station(tmp_path):
    station, rig = alignment_station(tmp_path)
    rig.light.halt = Mock()
    rig.light.start = Mock()
    rig.light.stop = Mock()
    return station, rig


def test_manual_switch_acknowledges_only_lamp_and_preserves_calibration(tmp_path):
    station, rig = light_station(tmp_path)
    station.calibrated = True
    try:
        assert station.set_manual_light(True) == "Candling light on."
        assert rig.light.values["LIGHT"] == "1"
        assert station.set_manual_light(False) == "Candling light off."
        assert rig.light.values["LIGHT"] == "0"
        assert [(role, text) for role, text, _ in rig.calls] == [
            ("LIGHT_CONTROLLER", "ACK_FAULT"), ("LIGHT_CONTROLLER", "LIGHT_ON"),
            ("LIGHT_CONTROLLER", "LIGHT_OFF")]
        assert station.calibrated
        station.inference.predict.assert_not_called()
        station.camera.apply_settings.assert_not_called()
    finally:
        station.stop()


def test_disconnected_station_opens_only_saved_light_port_and_releases_it(tmp_path, monkeypatch):
    station, rig = light_station(tmp_path)
    station.boards = None
    factory = Mock(return_value=rig.light)
    monkeypatch.setattr("src.core.station.BoardLink", factory)
    try:
        station.set_manual_light(True)
        assert factory.call_args.args[:2] == ("LIGHT_CONTROLLER", "COM9")
        assert factory.call_args.kwargs["protocol"] == 3
        assert station.boards is None and station.light_link is rig.light
        rig.light.start.assert_called_once()
        station.release_manual_light()
        rig.light.stop.assert_called_once()
        assert station.light_link is None and station._manual_light_cancel.is_set()
    finally:
        station.stop()


def test_explicit_retry_reopens_only_disconnected_lamp(tmp_path, monkeypatch):
    station, rig = light_station(tmp_path)
    _, replacement = light_station(tmp_path / "replacement")
    station.boards = None
    factory = Mock(side_effect=[rig.light, replacement.light])
    monkeypatch.setattr("src.core.station.BoardLink", factory)
    try:
        station.set_manual_light(True)
        rig.light.snapshot = lambda: SimpleNamespace(connected=False, identified=False,
            error="USB disconnected", telemetry={"LIGHT": "1"})
        station.set_manual_light(True)
        assert factory.call_count == 2 and station.light_link is replacement.light
        rig.light.stop.assert_called_once()
        assert replacement.light.values["LIGHT"] == "1" and station.boards is None
    finally:
        station.stop()


@pytest.mark.parametrize("kind", ["active", "moving", "profile", "fault", "cancelled"])
def test_unsafe_or_cancelled_manual_requests_never_dispatch(tmp_path, kind):
    station, rig = light_station(tmp_path)
    cancel = threading.Event()
    if kind == "active":
        station.cycle = SimpleNamespace(active=True)
    elif kind == "moving":
        rig.conveyor.values["BUSY"] = "1"
    elif kind == "profile":
        station.settings.rig_profile = "dual_v2"
    elif kind == "fault":
        rig.light.values["FAULT"] = "LINK_TIMEOUT"
    else:
        cancel.set()
    with pytest.raises(RuntimeError):
        station.set_manual_light(True, cancel)
    assert not rig.calls
    station._manual_light_cancel.set()


def test_watchdog_renewal_stops_on_release_and_halt(tmp_path):
    station, rig = light_station(tmp_path)
    station._manual_light_interval = .02
    try:
        station.set_manual_light(True)
        deadline = time.monotonic() + 1
        while sum(text == "LIGHT_ON" for _, text, _ in rig.calls) < 2 and time.monotonic() < deadline:
            time.sleep(.005)
        assert sum(text == "LIGHT_ON" for _, text, _ in rig.calls) >= 2
        station.release_manual_light()
        count = len(rig.calls)
        time.sleep(.06)
        assert len(rig.calls) == count and rig.light.values["LIGHT"] == "0"
        station.set_manual_light(True)
        station.halt()
        count = len(rig.calls)
        time.sleep(.06)
        assert station._manual_light_cancel.is_set() and len(rig.calls) == count
        assert rig.halts > 0
    finally:
        station.stop()


def test_failed_ack_or_stop_during_light_on_cannot_restart_lamp(tmp_path):
    station, rig = light_station(tmp_path)
    def stop_in_flight(role, text):
        if text == "LIGHT_ON":
            station.halt()
    rig.before_command = stop_in_flight
    with pytest.raises(RuntimeError, match="stopped"):
        station.set_manual_light(True)
    assert station._manual_light_cancel.is_set()
    rig.light.halt.assert_called()
    rig.calls.clear()
    rig.before_command = lambda *args: None
    original = rig.light.command
    def wrong_ack(text, timeout=3):
        future = original(text, timeout)
        if text == "LIGHT_ON":
            future.result()["LIGHT"] = "0"
        return future
    rig.light.command = wrong_ack
    with pytest.raises(RuntimeError, match="confirm"):
        station.set_manual_light(True)
    assert station._manual_light_cancel.is_set()


def test_alignment_finish_cancels_manual_renewal_before_lamp_off(tmp_path):
    station, rig = light_station(tmp_path)
    station._manual_light_interval = .02
    station.prepare_camera_alignment(True)
    try:
        station.set_manual_light(True)
        station.finish_camera_alignment()
        count = len(rig.calls)
        time.sleep(.06)
        assert len(rig.calls) == count and rig.light.values["LIGHT"] == "0"
    finally:
        station.stop()


def test_start_handoff_switches_manual_lamp_off_before_readiness_check(tmp_path):
    station, rig = light_station(tmp_path)
    station._manual_light_interval = .02
    station.calibrated = True
    station.inference.engine.engine_type = "ONNX"
    station.inference.engine.model_contract_verified = True
    rig.require_ready = Mock(side_effect=RuntimeError("readiness check reached"))
    try:
        station.set_manual_light(True)
        with pytest.raises(RuntimeError, match="readiness check reached"):
            station.start_cycle("BATCH-2026-10-KAY-01", 5, "Operator")
        rig.require_ready.assert_called_once()
        count = len(rig.calls)
        time.sleep(.06)
        assert rig.light.values["LIGHT"] == "0" and len(rig.calls) == count
        assert not station.active
    finally:
        station.stop()


def test_native_light_control_camera_tuning_feedback_and_cancel(hidden_ui, tmp_path, monkeypatch):
    app, _, _ = preview_app(tmp_path)
    _, rig = light_station(tmp_path / "rig")
    monkeypatch.setattr("src.core.station.BoardLink", Mock(return_value=rig.light))
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.deiconify()
        app.open_camera_controls()
        for width, height in ((1280, 860), (1024, 720)):
            app.geometry(f"{width}x{height}")
            app.update()
            for control in (app.light_btn, app.eject_btn, app._camera_panel.done):
                assert control.winfo_ismapped()
                assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
                assert control.winfo_rooty() + control.winfo_height() <= app.winfo_rooty() + app.winfo_height()
        app.light_btn.invoke()
        assert app._light_busy and app.light_btn.cget("state") == "disabled"
        pump(app, lambda: not app._light_busy)
        assert app.light_btn.cget("text") == "Turn light off"
        app.light_btn.invoke()
        pump(app, lambda: not app._light_busy)
        assert app.light_btn.cget("text") == "Turn light on"
        app._scan_busy = True
        app._refresh_light_control()
        assert app.light_btn.cget("state") == "disabled"
        app._scan_busy = False
        app.station.cycle = SimpleNamespace(active=True)
        app._refresh_light_control()
        assert app.light_btn.cget("text") == "Light: OFF" and app.light_btn.cget("state") == "disabled"
        app.station.cycle = None
        app._refresh_light_control()
        setter = app.station.set_manual_light
        app.station.set_manual_light = Mock(side_effect=RuntimeError("USB light controller unavailable"))
        app.light_btn.invoke()
        pump(app, lambda: not app._light_busy)
        assert app.light_btn.cget("text") == "Turn light on"
        assert "USB light controller unavailable" in app.log_textbox.get("1.0", "end")
        app.station.set_manual_light = setter
        snapshot = rig.light.snapshot
        rig.light.snapshot = lambda: SimpleNamespace(connected=False, identified=False,
            error="USB disconnected", telemetry={"LIGHT": "1"})
        app._refresh_light_control()
        assert app.light_btn.cget("text") == "Retry light"  # Stale ON is not confirmation.
        rig.light.snapshot = snapshot
        app._refresh_light_control()
        # STOP cancels a queued request before it ever reaches serial.
        queued = []
        submit = app._jobs.submit
        app._jobs.submit = lambda *args: queued.append(args)
        rig.calls.clear()
        app.light_btn.invoke()
        app.trigger_manual_eject()
        work, success, _ = queued.pop()
        success(work())
        app._jobs.submit = submit
        assert not rig.calls and not app._light_busy
        assert not errors
    finally:
        app.station.stop()
        app.shutdown()
        if app.winfo_exists():
            app.destroy()
