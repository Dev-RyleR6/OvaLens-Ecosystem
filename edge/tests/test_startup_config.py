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
        assert window._port_var.get() == "Auto-Detect"
        window._on_cancel()
    finally:
        try:
            window.destroy()
        except tk.TclError:
            pass


def test_operator_window_and_shutdown_without_hardware(hidden_ui):
    camera = SimpleNamespace(is_running=False, current_fps=0.0, last_error=None,
                             is_mock_mode=False, stop=Mock())
    sync = SimpleNamespace(last_error=None, is_online=False, stop=Mock())
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
