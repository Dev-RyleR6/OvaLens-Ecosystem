"""TASK-NEW-EDGE-MODEL-V3-01: model choice must preserve explicit overrides."""
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.inference import InferenceEngine


@pytest.mark.parametrize("v3_present", [True, False])
@pytest.mark.parametrize("override", [None, "environment", "argument"])
def test_model_selection_precedence(tmp_path, monkeypatch, v3_present, override):
    monkeypatch.delenv("ONNX_MODEL_PATH", raising=False)
    monkeypatch.setattr(InferenceEngine, "_load_engine", lambda self: None)
    monkeypatch.setattr(InferenceEngine, "_warmup", lambda self: None)
    (tmp_path / "best.onnx").write_bytes(b"old")
    if v3_present:
        (tmp_path / "best_v3.onnx").write_bytes(b"new")
    explicit = tmp_path / "explicit.onnx"
    if override:
        monkeypatch.setenv("ONNX_MODEL_PATH", str(explicit))
    argument = str(tmp_path / "argument.onnx") if override == "argument" else None
    engine = InferenceEngine(weights_dir=str(tmp_path), onnx_path=argument)
    expected = argument or (str(explicit) if override else
                           str(tmp_path / ("best_v3.onnx" if v3_present else "best.onnx")))
    assert engine.onnx_path == expected


def test_invalid_installed_v3_does_not_silently_switch_to_previous_onnx(tmp_path, monkeypatch):
    monkeypatch.delenv("ONNX_MODEL_PATH", raising=False)
    monkeypatch.setattr(InferenceEngine, "_warmup", lambda self: None)
    monkeypatch.setattr("src.core.inference._HAVE_YOLO", False)
    monkeypatch.setattr("src.core.inference._HAVE_ONNX", True)
    load = Mock(side_effect=ValueError("Invalid model contract"))
    monkeypatch.setattr("src.core.inference.ort.InferenceSession", load)
    for name in ("best.onnx", "best_v3.onnx"):
        (tmp_path / name).write_bytes(b"invalid")
    engine = InferenceEngine(weights_dir=str(tmp_path))
    assert load.call_count == 1
    assert load.call_args.args[0] == str(tmp_path / "best_v3.onnx")
    assert not engine.model_contract_verified and not engine.engine_type.startswith("ONNX")


def test_packaged_v3_contract_and_blank_image_require_review():
    import numpy as np
    path = Path(__file__).resolve().parents[1] / "models" / "weights" / "best_v3.onnx"
    engine = InferenceEngine(onnx_path=str(path), conf_threshold=.3, iou_threshold=.45)
    assert engine.model_contract_verified and engine.engine_type.startswith("ONNX")
    assert engine.model_identity["input_type"] == "tensor(float)"
    assert engine.model_identity["classes"] == {0: "Fertile", 1: "Infertile"}
    result = engine.predict(np.zeros((720, 1280, 3), dtype=np.uint8))
    assert result["final_class"] is None
    assert result["routing_action"] == "MANUAL_REVIEW" and result["confidence"] == 0
