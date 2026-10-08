"""TASK-NEW-EDGE-SETUP-01: software-only default setup and cancellation."""
from pathlib import Path
from types import SimpleNamespace
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.settings import EdgeSettings, SettingsStore
from src.core.station import EdgeStation
from src.db.local_db import LocalDatabaseManager
from src.iot.three_board import ROLES, ThreeBoardController, discover_boards
from test_three_board import Wire


def station_fixture(tmp_path, monkeypatch, roles=None):
    roles = roles or dict(zip(("COM5", "COM7", "COM9"), ROLES))
    opened, wires, applied = [], [], []
    def factory(port, *args, **kwargs):
        opened.append(port)
        wire = Wire(roles[port])
        wires.append(wire)
        return wire
    def discover(**kwargs):
        return discover_boards(serial_factory=factory, timeout=.05, **kwargs)
    monkeypatch.setattr("src.iot.three_board.list_ports.comports", lambda: [SimpleNamespace(device=p) for p in roles])
    monkeypatch.setattr("src.core.station.discover_boards", discover)
    monkeypatch.setattr("src.core.station.ThreeBoardController", lambda *ports: ThreeBoardController(*ports, serial_factory=factory))
    def apply(settings):
        applied.append(settings)
        return {"identity": f"opencv:{settings.index}:DSHOW", "properties": {}}
    camera = SimpleNamespace(apply_settings=apply, is_mock_mode=False, last_error=None,
                             snapshot=lambda: object())
    inference = SimpleNamespace(engine=SimpleNamespace(model_contract_verified=True),
                                predict=lambda work, **kwargs: work())
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    station = EdgeStation(camera, inference, db, "station", SettingsStore(tmp_path / "settings.json"))
    return station, opened, wires, applied


def commands(wires):
    return [line.split(" ", 1)[1] for wire in wires for line in wire.writes if line.startswith("@")]


def test_defaults_detect_and_prepare_without_conveyor_travel(tmp_path, monkeypatch):
    station, opened, wires, applied = station_fixture(tmp_path, monkeypatch)
    try:
        message = station.use_defaults_and_detect()
        assert "COM5" in message and "COM7" in message and "COM9" in message
        assert opened[:3] == ["COM5", "COM7", "COM9"]
        assert len(applied) == 1 and applied[0].index == 0
        assert station.store.load().snapshot() == station.settings.snapshot()
        assert not station.calibrated and not commands(wires)
        assert all(link.snapshot().telemetry["FAULT"] == "STARTUP_ACK_REQUIRED" for link in station.board_links())
        assert "Ready" in station.prepare_empty_conveyor(True)
        assert station.calibrated
        sent = commands(wires)
        assert sent.count("ACK_FAULT") == 3
        assert "SETHOME" in sent and "PAUSE" in sent and "LIGHT_OFF" in sent
        assert "RESET" in sent and "SET_FERTILE:180" in sent
        assert not any(c.startswith(("JOG:", "ADVANCE:", "SORT:", "RESUME")) for c in sent)
        assert station.db.load_machine_state("station")["state"] == "CLEARED"
    finally:
        station.stop()


def test_detection_uses_roles_when_usb_port_order_changes(tmp_path, monkeypatch):
    roles = dict(zip(("COM9", "COM5", "COM7"), ROLES))
    station, opened, wires, _ = station_fixture(tmp_path, monkeypatch, roles)
    try:
        station.use_defaults_and_detect()
        assert (station.settings.conveyor_port, station.settings.servo_port, station.settings.light_port) == ("COM9", "COM5", "COM7")
        assert not commands(wires)
    finally:
        station.stop()


def test_discovery_falls_back_after_preferred_ports_and_stops_when_complete(monkeypatch):
    roles = dict(zip(("COM11", "COM12", "COM13"), ROLES))
    opened = []
    def factory(port, *args, **kwargs):
        import serial
        opened.append(port)
        if port not in roles:
            raise serial.SerialException("Port unavailable")
        return Wire(roles[port])
    monkeypatch.setattr("src.iot.three_board.list_ports.comports", lambda: [SimpleNamespace(device=p) for p in (*roles, "COM99")])
    assert discover_boards(serial_factory=factory, timeout=.03) == dict(zip(ROLES, roles))
    assert opened == ["COM5", "COM7", "COM9", "COM11", "COM12", "COM13"]


@pytest.mark.parametrize("fault", ["unchecked", "sensor", "camera", "model"])
def test_preparation_requires_inspection_clear_sensor_camera_and_model(tmp_path, monkeypatch, fault):
    station, _, wires, _ = station_fixture(tmp_path, monkeypatch)
    try:
        station.use_defaults_and_detect()
        if fault == "sensor":
            station.boards.egg.state.telemetry["SENSOR"] = "1"
        elif fault == "camera":
            station.camera.last_error = "disconnected"
        elif fault == "model":
            station.inference.engine.model_contract_verified = False
        with pytest.raises(RuntimeError):
            station.prepare_empty_conveyor(fault != "unchecked")
        assert not station.calibrated and not commands(wires)
    finally:
        station.stop()


def test_stop_during_discovery_cannot_apply_connect_or_save(tmp_path, monkeypatch):
    station, opened, wires, applied = station_fixture(tmp_path, monkeypatch)
    def stopped_discovery(**kwargs):
        station.halt()
        return dict(zip(ROLES, ("COM5", "COM7", "COM9")))
    monkeypatch.setattr("src.core.station.discover_boards", stopped_discovery)
    with pytest.raises(RuntimeError, match="Setup stopped"):
        station.use_defaults_and_detect()
    assert not opened and not applied and not station.store.path.exists()
    assert station.boards is None and not station.calibrated


def test_stop_during_preparation_prevents_remaining_gate_commands(tmp_path, monkeypatch):
    station, _, wires, _ = station_fixture(tmp_path, monkeypatch)
    try:
        station.use_defaults_and_detect()
        original = station.boards.conveyor.command
        def stopped(command, timeout=3):
            result = original(command, timeout)
            if command.startswith("SPEED:"):
                station.halt()
            return result
        station.boards.conveyor.command = stopped
        with pytest.raises(RuntimeError):
            station.prepare_empty_conveyor(True)
        assert not station.calibrated
        assert "RESET" not in commands(wires)
    finally:
        station.stop()


def test_cancelled_discovery_closes_port_without_actuating(monkeypatch):
    cancel = threading.Event()
    wire = Wire("CONVEYOR")
    def factory(*args, **kwargs):
        cancel.set()
        return wire
    with pytest.raises(RuntimeError, match="Setup stopped"):
        discover_boards(["COM5"], factory, timeout=.03, cancel=cancel)
    assert wire.closed and not wire.writes


def test_new_defaults_remember_user_port_mapping():
    settings = EdgeSettings.three_board().validate()
    assert (settings.conveyor_port, settings.servo_port, settings.light_port) == ("COM5", "COM7", "COM9")
