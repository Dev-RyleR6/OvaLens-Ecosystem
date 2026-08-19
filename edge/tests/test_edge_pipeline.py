import os
import sys
import uuid
import numpy as np
import pytest

# Add edge root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.heuristics import CandlingHeuristics
from src.core.camera import CameraGrabber
from src.core.inference import InferenceEngine
from src.iot.serial_driver import ESP32SerialDriver
from src.db.local_db import LocalDatabaseManager


def test_candling_heuristics():
    # Test aspect ratio
    assert CandlingHeuristics.validate_aspect_ratio(100, 100) is True   # AR 1.0 (Valid)
    assert CandlingHeuristics.validate_aspect_ratio(80, 100) is True    # AR 0.8 (Valid)
    assert CandlingHeuristics.validate_aspect_ratio(20, 100) is False   # AR 0.2 (Too thin)
    assert CandlingHeuristics.validate_aspect_ratio(200, 100) is False  # AR 2.0 (Too wide)

    # Test optical luminance on white vs black frame
    white_frame = np.full((400, 400, 3), 255, dtype=np.uint8)
    lum_info = CandlingHeuristics.calculate_candling_luminance(white_frame, (0.5, 0.5, 0.5, 0.5))
    assert lum_info["mean_luminance"] > 200.0


def test_camera_mock_generation():
    camera = CameraGrabber()
    mock_frame = camera._generate_mock_candling_frame()
    assert mock_frame is not None
    assert mock_frame.shape == (720, 1280, 3)


def test_inference_engine():
    engine = InferenceEngine()
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    result = engine.predict(test_frame)

    assert "final_class" in result
    assert result["final_class"] in ["FERTILE", "INFERTILE", "ABNORMAL"]
    assert "routing_action" in result
    assert result["routing_action"] in ["ACCEPT", "REJECT"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["inference_ms"] >= 0


def test_local_sqlite_wal(tmp_path):
    test_db_path = str(tmp_path / "test_scans.db")
    db = LocalDatabaseManager(db_path=test_db_path)

    sess_id = str(uuid.uuid4())
    db.create_session(
        session_id=sess_id,
        batch_id="TEST-BATCH-01",
        device_id="TEST-STATION",
        stage="DAY_10",
        operator_name="Tester"
    )

    # Record 3 scans: 2 Fertile, 1 Infertile
    s1 = str(uuid.uuid4())
    s2 = str(uuid.uuid4())
    s3 = str(uuid.uuid4())

    db.record_scan(s1, sess_id, "TEST-BATCH-01", 1, "FERTILE", 0.95, 25, "ACCEPT", [])
    db.record_scan(s2, sess_id, "TEST-BATCH-01", 2, "FERTILE", 0.92, 30, "ACCEPT", [])
    db.record_scan(s3, sess_id, "TEST-BATCH-01", 3, "INFERTILE", 0.88, 28, "REJECT", [])

    # Check session counters
    stats = db.get_session_stats(sess_id)
    assert stats["total_scanned"] == 3
    assert stats["fertile_count"] == 2
    assert stats["infertile_count"] == 1
    assert stats["abnormal_count"] == 0

    # Check uncommitted queue
    uncommitted = db.get_uncommitted_scans(limit=10)
    assert len(uncommitted) == 3

    # Mark s1, s2 as synced
    db.mark_scans_synced([s1, s2])
    remaining = db.get_uncommitted_scans(limit=10)
    assert len(remaining) == 1
    assert remaining[0]["scan_id"] == s3


def test_esp32_serial_mock():
    iot = ESP32SerialDriver()
    iot.schedule_ejection(delay_ms=2000, pulse_ms=250)
    iot.set_candling_light(255)
    iot.ping()
    assert iot.is_connected is False  # Mock mode verified
