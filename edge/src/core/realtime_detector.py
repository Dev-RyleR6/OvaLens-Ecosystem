"""
Real-time candling egg detector and bounding box tracker.
Provides asynchronous, non-blocking real-time egg localization and coordinate smoothing.
"""

import threading
import time
from typing import List, Dict, Any, Optional
import numpy as np

from .heuristics import CandlingHeuristics


class RealtimeEggTracker:
    """
    Tracks and smooths egg bounding box detections across video frames
    using an Exponential Moving Average (EMA) filter.
    Eliminates high-frequency coordinate jitter while preserving rapid tracking response.
    """

    def __init__(self, alpha: float = 0.60):
        self.alpha = alpha
        self.smoothed_bbox: Optional[List[float]] = None
        self.current_detection: Optional[Dict[str, Any]] = None
        self.last_update_time: float = 0.0

    def update(self, detection: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        if detection is None:
            # If no detection for > 0.40s, clear smoothed box
            if now - self.last_update_time > 0.40:
                self.smoothed_bbox = None
                self.current_detection = None
                return None
            return self.current_detection

        raw_bbox = detection.get("bbox", [])
        if len(raw_bbox) != 4:
            self.smoothed_bbox = None
            self.current_detection = None
            return None

        if self.smoothed_bbox is None or (now - self.last_update_time > 0.50):
            self.smoothed_bbox = [float(v) for v in raw_bbox]
        else:
            self.smoothed_bbox = [
                round(self.alpha * float(r) + (1.0 - self.alpha) * float(s), 4)
                for r, s in zip(raw_bbox, self.smoothed_bbox)
            ]

        self.last_update_time = now
        self.current_detection = {
            **detection,
            "bbox": list(self.smoothed_bbox),
            "timestamp": now,
        }
        return self.current_detection

    def clear(self):
        self.smoothed_bbox = None
        self.current_detection = None
        self.last_update_time = 0.0


class RealtimeDetectionWorker:
    """
    Dedicated background worker for real-time egg detection on the live camera stream.
    Decoupled from the GUI render loop and formal single-scan persistence.
    """

    def __init__(self, camera: Any, engine: Any, target_fps: float = 20.0):
        self.camera = camera
        self.engine = engine
        self.target_interval = 1.0 / max(1.0, target_fps)
        self.tracker = RealtimeEggTracker(alpha=0.65)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()
        self._latest_detection: Optional[Dict[str, Any]] = None
        self._thread: Optional[threading.Thread] = None
        self._last_frame_sequence = None
        self.last_error = None

    def start(self):
        self._stop_event.clear()
        self._pause_event.clear()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="OvaLens-RealtimeDetector",
            )
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

    def pause(self):
        """Temporarily pause real-time preview inference (e.g. during formal scan or standby)."""
        self._pause_event.set()
        self.clear()

    def resume(self):
        """Resume real-time preview inference."""
        self._pause_event.clear()

    def clear(self):
        """Immediately discard any buffered live detection."""
        with self._lock:
            self._latest_detection = None
        self.tracker.clear()

    @property
    def latest_detection(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._latest_detection and (time.monotonic() - self._latest_detection.get("timestamp", 0) < 0.45):
                return dict(self._latest_detection)
            return None

    def _run(self):
        while not self._stop_event.is_set():
            t_start = time.monotonic()

            if self._pause_event.is_set():
                time.sleep(0.02)
                continue

            if not getattr(self.camera, "is_running", False):
                time.sleep(0.04)
                continue

            get_frame = getattr(self.camera, "get_latest_frame", None)
            if not callable(get_frame):
                time.sleep(0.04)
                continue

            snapshot_fn = getattr(self.camera, "snapshot", None)
            snapshot = snapshot_fn() if callable(snapshot_fn) else None
            if snapshot is not None:
                if snapshot.sequence == self._last_frame_sequence:
                    self._stop_event.wait(.01)
                    continue
                self._last_frame_sequence = snapshot.sequence
                frame = snapshot.image
            else:
                frame = get_frame(copy=True)
            if frame is None:
                time.sleep(0.02)
                continue

            try:
                # Fast predict via inference engine
                predict_fn = getattr(self.engine, "predict", None)
                if callable(predict_fn):
                    result = predict_fn(frame)
                    if self._pause_event.is_set() or self._stop_event.is_set():
                        continue
                    if snapshot is not None and snapshot.settings_revision != self.camera.settings_revision:
                        continue
                    detections = result.get("detections", [])
                    primary = CandlingHeuristics.filter_and_rank_detections(detections, frame)

                    smoothed = self.tracker.update(primary)
                    with self._lock:
                        self._latest_detection = smoothed
            except Exception as exc:
                # Discard transient camera / inference exceptions cleanly
                self.last_error = str(exc)

            elapsed = time.monotonic() - t_start
            sleep_time = max(0.005, self.target_interval - elapsed)
            time.sleep(sleep_time)
