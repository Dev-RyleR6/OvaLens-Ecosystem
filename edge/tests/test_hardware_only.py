"""TASK-NEW-EDGE-HARDWAREONLY-01: unavailable equipment never becomes simulation."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.inference import InferenceEngine
from src.core.readiness import StationReadiness
from src.iot.serial_driver import ESP32SerialDriver


@pytest.mark.parametrize("runtime_installed", [True, False])
def test_missing_model_cannot_classify_or_pass_readiness(tmp_path, monkeypatch, runtime_installed):
    monkeypatch.delenv("ONNX_MODEL_PATH", raising=False)
    monkeypatch.setattr("src.core.inference._HAVE_ONNX", runtime_installed)
    monkeypatch.setattr("src.core.inference._HAVE_YOLO", False)
    engine = InferenceEngine(weights_dir=str(tmp_path))
    assert engine.engine_type == "UNAVAILABLE"
    assert not engine.model_contract_verified and not engine.warmup_complete
    assert "Model unavailable" in engine.load_error
    # Image brightness/texture must never be substituted for a model prediction.
    for brightness in (0, 100, 255):
        result = engine.predict(np.full((32, 32, 3), brightness, dtype=np.uint8))
        assert result["final_class"] is None and result["confidence"] == 0
        assert result["detections"] == []
        assert result["routing_action"] == "MANUAL_REVIEW"
        assert result["error_code"] == "MODEL_UNAVAILABLE"
    readiness = StationReadiness(SimpleNamespace(inference=SimpleNamespace(engine=engine)))
    with pytest.raises(RuntimeError, match="Model unavailable"):
        readiness._model()


@pytest.mark.parametrize("warmup_fails", [True, False])
def test_warmup_requires_three_successful_real_inference_passes(monkeypatch, warmup_fails):
    inference = Mock(side_effect=RuntimeError("execution failed") if warmup_fails else None,
                     return_value={"final_class": None})
    def load(engine):
        engine.engine_type = "ONNX Runtime (test transport)"
        engine.onnx_session = object()
        engine.model_contract_verified = True
        engine.model_identity = {"sha256": "test"}
        engine._infer_onnx = inference
    monkeypatch.setattr(InferenceEngine, "_load_engine", load)
    engine = InferenceEngine()
    if warmup_fails:
        assert engine.engine_type == "UNAVAILABLE"
        assert not engine.warmup_complete and not engine.model_contract_verified
        assert engine.onnx_session is None and engine.model_identity == {}
        assert "Startup warmup failed" in engine.load_error
        assert engine.predict(np.zeros((32, 32, 3), dtype=np.uint8))["final_class"] is None
        assert inference.call_count == 1
    else:
        assert engine.warmup_complete and engine.model_contract_verified
        assert inference.call_count == 3


def test_absent_serial_hardware_fails_without_starting_worker(monkeypatch):
    monkeypatch.setattr("serial.tools.list_ports.comports", lambda: [])
    driver = ESP32SerialDriver()
    with pytest.raises(ConnectionError, match="ESP32 unavailable"):
        driver.start()
    assert not driver.is_connected and not driver._is_running
    assert driver._reader_thread is None


def test_serial_open_failure_cannot_accept_commands(monkeypatch):
    monkeypatch.setattr("serial.Serial", Mock(side_effect=OSError("USB disconnected")))
    driver = ESP32SerialDriver(port="TEST-PORT")
    with pytest.raises(ConnectionError, match="USB disconnected"):
        driver.start()
    with pytest.raises(ConnectionError, match="USB disconnected"):
        driver.set_conveyor(True)
    assert not driver.is_connected and not driver._is_running


def test_serial_commands_use_real_transport_and_report_write_failure(monkeypatch):
    wire = Mock(is_open=True)
    monkeypatch.setattr("serial.Serial", Mock(return_value=wire))
    driver = ESP32SerialDriver(port="TEST-PORT")
    driver._connect()
    driver.ping()
    wire.write.assert_called_once_with(b"CMD:PING\n")
    wire.write.side_effect = OSError("USB disconnected")
    with pytest.raises(ConnectionError, match="Serial write failure"):
        driver.set_conveyor(True)
    assert not driver.is_connected
    wire.close.assert_called_once()


def test_serial_disconnect_stops_worker_without_reopening_hardware(monkeypatch):
    wire = Mock(is_open=True, in_waiting=1)
    wire.readline.side_effect = OSError("USB disconnected")
    connect = Mock(return_value=wire)
    monkeypatch.setattr("serial.Serial", connect)
    driver = ESP32SerialDriver(port="TEST-PORT")
    driver._connect()
    driver._is_running = True
    driver._read_loop()
    assert not driver._is_running and not driver.is_connected
    assert "ESP32 disconnected" in driver.last_error
    connect.assert_called_once()
