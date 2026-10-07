"""
Automated unit tests for RealtimeEggTracker and RealtimeDetectionWorker.
Verifies zero-latency real-time bounding box tracking, coordinate smoothing, and preview/scan lifecycle.
"""

import time
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
import pytest

from edge.src.core.realtime_detector import RealtimeEggTracker, RealtimeDetectionWorker
from edge.src.core.heuristics import CandlingHeuristics
from edge.src.ui.app import OvaLensOperatorApp


def test_egg_tracker_ema_smoothing():
    tracker = RealtimeEggTracker(alpha=0.50)

    # First observation initializes smoothed box
    det1 = {"bbox": [0.50, 0.50, 0.40, 0.60], "class": "FERTILE", "confidence": 0.95}
    res1 = tracker.update(det1)
    assert res1 is not None
    assert res1["bbox"] == [0.50, 0.50, 0.40, 0.60]

    # Second observation with jitter is smoothed by EMA (50% blend)
    det2 = {"bbox": [0.52, 0.48, 0.42, 0.58], "class": "FERTILE", "confidence": 0.94}
    res2 = tracker.update(det2)
    assert res2 is not None
    # Expected: 0.5 * 0.52 + 0.5 * 0.50 = 0.51
    assert round(res2["bbox"][0], 2) == 0.51
    assert round(res2["bbox"][1], 2) == 0.49
    assert round(res2["bbox"][2], 2) == 0.41
    assert round(res2["bbox"][3], 2) == 0.59


def test_egg_tracker_clears_on_timeout():
    tracker = RealtimeEggTracker(alpha=0.50)
    det = {"bbox": [0.50, 0.50, 0.40, 0.60], "class": "INFERTILE", "confidence": 0.90}
    tracker.update(det)

    tracker.last_update_time = time.monotonic() - 0.50
    res = tracker.update(None)
    assert res is None
    assert tracker.smoothed_bbox is None


def test_heuristics_rejects_invalid_candidates():
    # If detections fail aspect ratio or luminance on dark frame, return None instead of bogus box
    dark_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    invalid_detections = [
        {"bbox": [0.50, 0.50, 0.05, 0.90], "class": "FERTILE", "confidence": 0.85}  # Bad aspect ratio (0.05 / 0.90 = 0.055)
    ]
    result = CandlingHeuristics.filter_and_rank_detections(invalid_detections, dark_frame)
    assert result is None


def test_realtime_worker_lifecycle():
    camera = SimpleNamespace(
        is_running=True,
        get_latest_frame=Mock(return_value=np.zeros((480, 640, 3), dtype=np.uint8)),
    )
    engine = SimpleNamespace(
        predict=Mock(return_value={
            "detections": [{
                "bbox": [0.50, 0.50, 0.40, 0.50],
                "confidence": 0.92,
                "class": "FERTILE"
            }]
        })
    )

    worker = RealtimeDetectionWorker(camera, engine, target_fps=30.0)
    worker.start()
    time.sleep(0.08)

    # Verify pause and clear
    worker.pause()
    assert worker._pause_event.is_set()
    assert worker.latest_detection is None

    worker.resume()
    assert not worker._pause_event.is_set()

    worker.stop()
    assert worker._stop_event.is_set()
    assert worker.latest_detection is None


def test_get_active_display_detections():
    camera = SimpleNamespace(is_running=True)
    app = SimpleNamespace(
        camera=camera,
        _stopping=False,
        _scan_busy=False,
        _latest_detections=[],
        _last_scan_result_time=0.0,
        realtime_detector=None,
    )

    # 1. Fallback when idle and no detections
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert detections == []

    # 2. Real-time background detection present
    mock_live = {"bbox": [0.5, 0.5, 0.3, 0.4], "class": "FERTILE", "confidence": 0.90}
    app.realtime_detector = SimpleNamespace(latest_detection=mock_live)
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert len(detections) == 1
    assert detections[0]["class"] == "FERTILE"

    # 3. Scanning lock active
    app._scan_busy = True
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert len(detections) == 1
    assert detections[0].get("is_scanning") is True

    # 4. Fresh single scan result takes precedence within 1.5s
    app._scan_busy = False
    app._latest_detections = [{"bbox": [0.5, 0.5, 0.3, 0.4], "class": "INFERTILE", "confidence": 0.95}]
    app._last_scan_result_time = time.monotonic()
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert len(detections) == 1
    assert detections[0]["class"] == "INFERTILE"

    # 5. After 1.5s, scan result expires; if no live detection, returns empty (NO STICKING)
    app._last_scan_result_time = time.monotonic() - 2.0
    app.realtime_detector.latest_detection = None
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert detections == []

    # 6. When session is stopping or camera is off, preview detections are immediately empty
    app._stopping = True
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert detections == []

    app._stopping = False
    camera.is_running = False
    detections = OvaLensOperatorApp._get_active_display_detections(app)
    assert detections == []


def test_inference_engine_thresholds():
    from edge.src.core.inference import InferenceEngine

    # Default thresholds should be 0.85 (85%)
    engine = InferenceEngine()
    assert engine.conf_threshold == 0.85
    assert engine.iou_threshold == 0.85

    # Percentage values 85 should be normalized to 0.85
    engine_pct = InferenceEngine(conf_threshold=85, iou_threshold=85)
    assert engine_pct.conf_threshold == 0.85
    assert engine_pct.iou_threshold == 0.85


def test_heuristics_accepts_valid_aspect_ratio_in_ambient_light():
    # Frame in ambient lighting (mean luminance < 30) with valid egg aspect ratio (0.40 / 0.50 = 0.80)
    dark_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    valid_egg_detections = [
        {"bbox": [0.50, 0.50, 0.40, 0.50], "class": "FERTILE", "confidence": 0.90}
    ]
    result = CandlingHeuristics.filter_and_rank_detections(valid_egg_detections, dark_frame)
    assert result is not None
    assert result["class"] == "FERTILE"
    assert result["confidence"] == 0.90
