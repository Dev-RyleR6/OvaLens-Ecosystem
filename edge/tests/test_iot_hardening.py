"""Automated tests for IoT hardening, serial resilience, Bluetooth port filtering,
delayed auto-reset race prevention, clean station manual light release, and app dependencies."""
import queue
import threading
import time
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tkinter as tk
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.station import EdgeStation
from src.core.settings import EdgeSettings
from src.iot.dual_board import BoardLink, BoardState
from src.iot.three_board import discover_boards, _is_ignored_port, ROLES
from src.ui.app import OvaLensOperatorApp


def test_is_ignored_port_filters_bluetooth_and_legacy_motherboard_ports():
    bt_port_1 = SimpleNamespace(device="COM3", hwid=r"BTHENUM\{00001101-0000-1000-8000-00805F9B34FB}", description="Standard Serial over Bluetooth link (COM3)", manufacturer="Microsoft")
    bt_port_2 = SimpleNamespace(device="COM4", hwid="", description="Bluetooth Serial Port (COM4)", manufacturer="")
    legacy_com1 = SimpleNamespace(device="COM1", hwid=r"ACPI\PNP0501\1", description="Communications Port (COM1)", manufacturer="Microsoft")
    usb_esp32_cp2102 = SimpleNamespace(device="COM5", hwid=r"USB\VID_10C4&PID_EA60\0001", description="Silicon Labs CP210x USB to UART Bridge (COM5)", manufacturer="Silicon Laboratories")
    usb_ch340 = SimpleNamespace(device="COM7", hwid=r"USB\VID_1A86&PID_7523\5", description="USB-SERIAL CH340 (COM7)", manufacturer="wch.cn")
    bare_port = SimpleNamespace(device="COM9")

    assert _is_ignored_port(bt_port_1) is True
    assert _is_ignored_port(bt_port_2) is True
    assert _is_ignored_port(legacy_com1) is True
    assert _is_ignored_port(usb_esp32_cp2102) is False
    assert _is_ignored_port(usb_ch340) is False
    assert _is_ignored_port(bare_port) is False


def test_discover_boards_ignores_bluetooth_and_legacy_devices(monkeypatch):
    ports = [
        SimpleNamespace(device="COM1", hwid=r"ACPI\PNP0501", description="Communications Port"),
        SimpleNamespace(device="COM3", hwid=r"BTHENUM\1234", description="Bluetooth Link"),
        SimpleNamespace(device="COM5", hwid=r"USB\VID_10C4", description="ESP32 Conveyor"),
        SimpleNamespace(device="COM7", hwid=r"USB\VID_10C4", description="ESP32 Egg"),
        SimpleNamespace(device="COM9", hwid=r"USB\VID_10C4", description="ESP32 Light"),
    ]
    monkeypatch.setattr("src.iot.three_board.list_ports.comports", lambda: ports)

    probed = []
    class MockWire:
        def __init__(self, port):
            self.port = port
            probed.append(port)
        def write(self, data):
            return len(data)
        def read(self, count):
            if self.port == "COM5":
                return b"PONG:CONVEYOR\nREADY:CONVEYOR_V3:PROTOCOL=3\n"
            if self.port == "COM7":
                return b"PONG:EGG_CONTROLLER\nREADY:EGG_CONTROLLER_V3:PROTOCOL=3\n"
            if self.port == "COM9":
                return b"PONG:LIGHT_CONTROLLER\nREADY:LIGHT_CONTROLLER_V3:PROTOCOL=3\n"
            return b""
        def close(self):
            pass

    found = discover_boards(preferred=("COM5", "COM7", "COM9"), serial_factory=lambda port, *a, **k: MockWire(port), timeout=0.1)
    assert found == {"CONVEYOR": "COM5", "EGG_CONTROLLER": "COM7", "LIGHT_CONTROLLER": "COM9"}
    assert "COM1" not in probed
    assert "COM3" not in probed


def test_board_link_retries_on_windows_port_locking_and_suppresses_dtr_rts():
    attempts = 0
    dtr_states = []
    rts_states = []
    buffer_resets = 0

    class MockSerialWithControls:
        def __init__(self, port, *a, **k):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise PermissionError("WinError 5: Access is denied")
            self._dtr = True
            self._rts = True
            self.writes = []

        @property
        def dtr(self):
            return self._dtr

        @dtr.setter
        def dtr(self, val):
            self._dtr = val
            dtr_states.append(val)

        @property
        def rts(self):
            return self._rts

        @rts.setter
        def rts(self, val):
            self._rts = val
            rts_states.append(val)

        def reset_input_buffer(self):
            nonlocal buffer_resets
            buffer_resets += 1

        def write(self, data):
            self.writes.append(data)
            return len(data)

        def read(self, count):
            time.sleep(0.01)
            return b"READY:CONVEYOR_V2:PROTOCOL=2\nSTATE:IDLE\n"

        def close(self):
            pass

    link = BoardLink("CONVEYOR", "COM5", serial_factory=MockSerialWithControls, protocol=2)
    link.start()
    try:
        deadline = time.monotonic() + 2.0
        while not link._status_complete and time.monotonic() < deadline:
            time.sleep(0.02)
        assert link.snapshot().connected is True
        assert attempts == 3
        assert False in dtr_states
        assert False in rts_states
        assert buffer_resets >= 1
    finally:
        link.stop()


def test_board_link_delayed_auto_reset_race_recovery_on_startup():
    failures = []
    link = BoardLink("CONVEYOR", "COM5", failures.append, protocol=3)
    link.state.connected = True
    now = time.monotonic()
    link._started_at = now
    # Initial quick handshake before delayed hardware reset trips
    link._receive("READY:CONVEYOR_V3:PROTOCOL=3", now)
    link._receive("STATE:WAITING", now)
    assert link._status_complete is True
    assert link.snapshot().identified is True

    # Hardware delayed reset emits BOOT during startup window before any commands dispatched
    link._receive("BOOT:CONVEYOR_V3", now + 0.2)
    # Must NOT fail the link; instead reset handshake state for clean re-handshake
    assert not failures
    assert link._status_complete is False
    assert link.snapshot().identified is False
    assert link.state.error == ""

    # Board emits its post-boot banner
    link._receive("READY:CONVEYOR_V3:PROTOCOL=3", now + 0.3)
    link._receive("STATE:WAITING", now + 0.35)
    assert link._status_complete is True
    assert link.snapshot().identified is True
    assert not failures


def test_board_link_boot_reset_fails_if_commands_already_dispatched():
    failures = []
    link = BoardLink("CONVEYOR", "COM5", failures.append, protocol=3)
    link.state.connected = True
    now = time.monotonic()
    link._started_at = now
    link._receive("READY:CONVEYOR_V3:PROTOCOL=3", now)
    link._receive("STATE:WAITING", now)
    assert link._status_complete is True

    # Simulate command was dispatched
    future = Future()
    future.deadline = now + 5
    link._pending = [1, "ACK_FAULT", now + 3, future, False]
    link._commands_dispatched = 1

    # Reset occurs during active command / operation -> MUST fail to prevent unsafe operation
    link._receive("BOOT:CONVEYOR_V3", now + 0.5)
    assert failures and "reset" in failures[-1]
    assert link.state.error == "Board reset; inspect and reconnect"
    assert future.done() and future.exception() is not None


def test_release_manual_light_cleanly_stops_and_releases_com():
    mock_link = Mock()
    mock_link.snapshot.return_value = SimpleNamespace(connected=True, error="", identified=True)
    mock_link.stop = Mock()

    station = EdgeStation(Mock(), Mock(), Mock(), "STATION-01")
    station._manual_light_link = mock_link
    station._manual_light_cancel.clear()

    t0 = time.monotonic()
    station.release_manual_light()
    elapsed = time.monotonic() - t0

    mock_link.stop.assert_called_once()
    assert station._manual_light_link is None
    assert station._manual_light_cancel.is_set()
    assert elapsed >= 0.14  # OS port release cooldown elapsed


def test_prepare_for_sorting_releases_manual_light_first():
    station = EdgeStation(Mock(), Mock(), Mock(), "STATION-01")
    station.settings.rig_profile = "three_v3"
    station.settings_error = ""
    station.boards = None
    mock_release = Mock()
    station.release_manual_light = mock_release

    with pytest.raises(RuntimeError, match="empty"):
        station.prepare_for_sorting(False, threading.Event())
    mock_release.assert_called_once()


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


def test_operator_app_station_dependency_without_legacy_iot_chamber(hidden_ui):
    camera = SimpleNamespace(is_running=False, current_fps=30.0, last_error=None,
                             is_mock_mode=False, stop=Mock())
    engine = Mock()
    db = Mock()
    db.get_batch_preferences.return_value = {}
    db.get_unsynced_count.return_value = 0
    db.get_distinct_batches.return_value = []
    db.get_scans_by_batch.return_value = []
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    worker = Mock()
    station = EdgeStation(camera, worker, db, "STATION-TEST")

    # Calling with explicit station and no iot/chamber keywords
    app = OvaLensOperatorApp(camera=camera, engine=engine, station=station,
                             db=db, sync_worker=sync, inference_worker=worker,
                             fullscreen=False)
    try:
        assert app.station is station
        assert app.iot is None
        assert app.chamber is None
    finally:
        try:
            app.destroy()
        except tk.TclError:
            pass


def test_operator_app_positional_station_resolution(hidden_ui):
    camera = SimpleNamespace(is_running=False, current_fps=30.0, last_error=None,
                             is_mock_mode=False, stop=Mock())
    engine = Mock()
    db = Mock()
    db.get_batch_preferences.return_value = {}
    db.get_unsynced_count.return_value = 0
    db.get_distinct_batches.return_value = []
    db.get_scans_by_batch.return_value = []
    sync = SimpleNamespace(last_error=None, heartbeat_error=None, is_online=False, stop=Mock())
    worker = Mock()
    station = EdgeStation(camera, worker, db, "STATION-TEST")

    # Calling with station in legacy iot positional slot
    app = OvaLensOperatorApp(camera, engine, station, db, sync, inference_worker=worker,
                             fullscreen=False)
    try:
        assert app.station is station
        assert app.iot is None
        assert app.chamber is None
    finally:
        try:
            app.destroy()
        except tk.TclError:
            pass

