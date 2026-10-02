"""Real camera/ONNX detection with bounded buffers and offline scan persistence."""

from dataclasses import dataclass
from pathlib import Path
import queue
import sys
import threading
import time
import uuid

import cv2
import numpy as np


@dataclass(frozen=True)
class VisionEvent:
    kind: str
    value: object


def primary_egg(result, frame):
    """Reject empty frames and invalid geometry rather than inferring an infertile egg."""
    height, width = frame.shape[:2]
    candidates = []
    for detection in result.get("detections", []):
        if detection.get("class") not in {"FERTILE", "INFERTILE"}:
            continue
        try:
            xc, yc, bw, bh = map(float, detection["bbox"])
            confidence = float(detection["confidence"])
        except (KeyError, TypeError, ValueError):
            continue
        if not all(np.isfinite(v) for v in (xc, yc, bw, bh, confidence)):
            continue
        if not (0 < bw <= 1 and 0 < bh <= 1 and 0 <= confidence <= 1):
            continue
        ratio = bw * width / (bh * height)
        if not (0.65 <= ratio <= 1.45 and bw * width * bh * height >= 4000):
            continue
        if not (0.2 <= xc <= 0.8 and 0.2 <= yc <= 0.8):
            continue
        x1, y1 = max(0, int((xc - bw / 2) * width)), max(0, int((yc - bh / 2) * height))
        x2, y2 = min(width, int((xc + bw / 2) * width)), min(height, int((yc + bh / 2) * height))
        roi = frame[y1:y2, x1:x2]
        if not roi.size or float(cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 2].mean()) < 30:
            continue
        candidates.append({**detection, "bbox": [xc, yc, bw, bh], "confidence": confidence,
                           "pixels": (x1, y1, x2, y2)})
    return max(candidates, key=lambda d: d["confidence"] -
               0.2 * ((d["bbox"][0] - 0.5) ** 2 + (d["bbox"][1] - 0.5) ** 2), default=None)


class PresenceLatch:
    """Record once per stable egg presence; require clear frames before rearming."""

    def __init__(self, stable_frames=3, clear_frames=5):
        self.stable_frames, self.clear_frames = stable_frames, clear_frames
        self.hits = self.misses = 0
        self.recorded = False
        self.last_class = None

    def observe(self, candidate):
        if candidate is None:
            self.misses += 1
            self.hits = 0
            if self.misses >= self.clear_frames:
                self.recorded, self.last_class = False, None
            return False
        self.misses = 0
        if candidate["class"] != self.last_class:
            self.hits = 0
            self.last_class = candidate["class"]
        self.hits += 1
        if not self.recorded and self.hits >= self.stable_frames:
            self.recorded = True
            return True
        return False


class RealCamera:
    """Continuous capture into one latest-frame slot; never synthesize missing hardware."""

    def __init__(self, index, events, capture_factory=cv2.VideoCapture):
        self.index, self.events, self.capture_factory = index, events, capture_factory
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.frame = None
        self.number = 0
        self.timestamp = 0.0
        self.fps = 0.0
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="OvaLens-Prototype-Camera")
        self._thread.start()

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    def snapshot(self):
        with self._lock:
            return self.number, self.timestamp, self.frame, self.fps

    def stop(self):
        self._stop.set()

    def _run(self):
        capture = None
        try:
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
            capture = self.capture_factory(self.index, backend)
            if not capture.isOpened():
                capture.release()
                capture = self.capture_factory(self.index)
            if not capture.isOpened():
                raise RuntimeError(f"Camera {self.index} is unavailable. Select another camera index.")
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            capture.set(cv2.CAP_PROP_FPS, 30)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            start, frames, misses = time.monotonic(), 0, 0
            while not self._stop.is_set():
                success, frame = capture.read()
                if not success or frame is None:
                    misses += 1
                    if misses >= 50:
                        raise RuntimeError("Camera stopped supplying frames. Check its USB connection.")
                    self._stop.wait(0.02)
                    continue
                misses = 0
                now = time.monotonic()
                frames += 1
                with self._lock:
                    self.frame, self.timestamp = frame, now
                    self.number += 1
                    if now - start >= 1:
                        self.fps = frames / (now - start)
                        start, frames = now, 0
        except Exception as exc:
            self.events.put(VisionEvent("error", str(exc)))
        finally:
            if capture is not None:
                capture.release()
            with self._lock:
                self.frame = None


def load_engine():
    # Support launch from either Capstone/ or firmware/.
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from edge.src.core.inference import InferenceEngine

    engine = InferenceEngine(conf_threshold=0.25)
    if not engine.engine_type.startswith("ONNX") or engine.onnx_session is None:
        raise RuntimeError("The real ONNX model could not load. Camera detection requires best.onnx.")
    shape = engine.onnx_session.get_outputs()[0].shape
    if len(shape) != 3 or shape[1] != 6:
        raise RuntimeError("The prototype requires a two-class YOLO detection model.")
    return engine


def load_store():
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from edge.src.db.local_db import LocalDatabaseManager
    return LocalDatabaseManager(db_path=str(Path(root) / "edge" / "db" / "prototype_scans.db"))


class VisionWorker:
    """Inference and SQLite run on a worker while capture/serial/UI remain independent."""

    def __init__(self, events, engine_factory=load_engine, store_factory=load_store,
                 camera_factory=RealCamera):
        self.events, self.engine_factory, self.store_factory = events, engine_factory, store_factory
        self.camera_factory = camera_factory
        self.camera = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.latest = None
        self.last_scan = None
        self.counts = {"FERTILE": 0, "INFERTILE": 0, "MANUAL_REVIEW": 0}
        self.session_id = None
        self.routed_id = None
        self.ready = False
        self._inspection_id = 0
        self._inspection_after = 0.0

    @property
    def active(self):
        return ((self._thread is not None and self._thread.is_alive()) or
                (self.camera is not None and self.camera.active))

    def start(self, camera_index=0):
        if self.active:
            raise ValueError("Stop the current camera session before starting another.")
        self._stop.clear()
        self.ready = False
        with self._lock:
            self.latest = self.last_scan = None
            self._inspection_id += 1
            self._inspection_after = 0.0
        self.routed_id = None
        self.counts = {"FERTILE": 0, "INFERTILE": 0, "MANUAL_REVIEW": 0}
        self.session_id = str(uuid.uuid4())
        self.camera = self.camera_factory(camera_index, self.events)
        self.camera.start()
        self._thread = threading.Thread(target=self._run, daemon=True, name="OvaLens-Prototype-Vision")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self.camera:
            self.camera.stop()

    def snapshot(self):
        with self._lock:
            return self.latest

    def begin_inspection(self, after):
        """Rearm only after a confirmed stationary cycle stop and settling time."""
        with self._lock:
            self._inspection_id += 1
            self._inspection_after = after
            self.latest = self.last_scan = None
            return self._inspection_id

    def suspend_inspection(self):
        """Keep draining camera frames, but do not classify eggs during travel."""
        return self.begin_inspection(float("inf"))

    def _run(self):
        store = None
        try:
            self.events.put(VisionEvent("status", "Loading model · 3 warmup passes"))
            engine = self.engine_factory()
            if self._stop.is_set():
                return
            store = self.store_factory()
            batch = f"PROTOTYPE-{self.session_id[:8]}"
            store.create_session(self.session_id, batch, "PROTOTYPE-COM5-COM7", "DAY_10", "Prototype operator")
            self.ready = True
            self.events.put(VisionEvent("status", "Camera detection running"))
            latch, last_frame, sequence, inspection_id = PresenceLatch(), -1, 0, -1
            while not self._stop.is_set():
                with self._lock:
                    current_id, after = self._inspection_id, self._inspection_after
                if current_id != inspection_id:
                    latch, inspection_id = PresenceLatch(), current_id
                number, stamp, frame, fps = self.camera.snapshot()
                if frame is None or number == last_frame or stamp < after or time.monotonic() - stamp > 0.5:
                    if not self.camera.active:
                        break
                    self._stop.wait(0.02)
                    continue
                started = time.perf_counter()
                last_frame = number
                result = engine.predict(frame)
                with self._lock:
                    if inspection_id != self._inspection_id:
                        continue
                candidate = primary_egg(result, frame)
                state = "NO_EGG" if candidate is None else (
                    "MANUAL_REVIEW" if candidate["confidence"] < 0.75 else candidate["class"])
                if latch.observe(candidate):
                    sequence += 1
                    action = "MANUAL_REVIEW" if state == "MANUAL_REVIEW" else (
                        "ACCEPT" if state == "FERTILE" else "REJECT")
                    scan = store.record_scan(str(uuid.uuid4()), self.session_id, batch, sequence,
                                             candidate["class"], candidate["confidence"],
                                             result["inference_ms"], action, result["detections"])
                    scan = {**scan, "recorded_at": time.monotonic(), "state": state,
                            "captured_at": stamp, "inspection_id": inspection_id}
                    with self._lock:
                        if inspection_id != self._inspection_id:
                            continue
                        self.last_scan = scan
                        self.counts[state] += 1
                    self.events.put(VisionEvent("scan", scan))
                elif not latch.recorded:
                    with self._lock:
                        self.last_scan = None
                with self._lock:
                    if inspection_id != self._inspection_id:
                        continue
                    self.latest = {"frame_number": number, "frame": frame, "timestamp": stamp,
                                   "inspection_id": inspection_id,
                                   "candidate": candidate, "state": state, "fps": fps,
                                   "inference_ms": result["inference_ms"], "engine": result["engine"],
                                   "counts": dict(self.counts), "last_scan": self.last_scan}
                # Bound inference to 10 Hz; camera continuously drains independently.
                self._stop.wait(max(0, 0.1 - (time.perf_counter() - started)))
        except Exception as exc:
            self.events.put(VisionEvent("error", str(exc)))
        finally:
            self.ready = False
            if self.camera:
                self.camera.stop()
            if store:
                try:
                    store.complete_session(self.session_id)
                except Exception as exc:
                    self.events.put(VisionEvent("error", f"Session persistence failed: {exc}"))
            with self._lock:
                self.latest = None
                self.last_scan = None
            self.events.put(VisionEvent("status", "Camera stopped"))

    def routable_scan(self):
        with self._lock:
            scan, latest = self.last_scan, self.latest
            if self._stop.is_set() or scan is None or latest is None or time.monotonic() - latest["timestamp"] > 0.5:
                raise ValueError("A fresh camera detection must be recorded before sorting.")
            if latest["state"] != scan["state"] or scan["state"] == "MANUAL_REVIEW":
                raise ValueError("Inspect this egg manually; the current detection is not ready to sort.")
            if time.monotonic() - scan["recorded_at"] > 10:
                raise ValueError("The saved scan is stale. Clear the camera zone and detect the next egg.")
            if scan["scan_id"] == self.routed_id:
                raise ValueError("A sort has already been requested for this recorded egg.")
            return dict(scan)

    def mark_routed(self, scan_id):
        with self._lock:
            self.routed_id = scan_id
