"""Detection, persistence, and bounded-work safeguards for TASK-NEW-FW-DET-01."""

from pathlib import Path
import queue
import sys
import threading
import time

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from firmware.prototype.controller import ControllerEvent, EventInbox, OpticalCounter
from firmware.prototype.vision import PresenceLatch, RealCamera, VisionWorker, primary_egg
from edge.src.db.local_db import LocalDatabaseManager


def candidate(confidence=0.95, cls="FERTILE", bbox=None):
    return {"class": cls, "confidence": confidence, "bbox": bbox or [0.5, 0.5, 0.2, 0.3]}


def wait_for(predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    pytest.fail("Worker did not reach the expected state")


def test_empty_or_invalid_frame_never_becomes_an_infertile_egg():
    bright = np.full((720, 1280, 3), 100, dtype=np.uint8)
    assert primary_egg({"final_class": "INFERTILE", "confidence": 0.85, "detections": []}, bright) is None
    for item in (candidate(bbox=[0.5, 0.5, 0.02, 0.02]),
                 candidate(bbox=[0.5, 0.5, 0.5, 0.1]),
                 candidate(bbox=[0.95, 0.5, 0.2, 0.3]),
                 candidate(confidence=float("nan")), candidate(cls="ABNORMAL")):
        assert primary_egg({"detections": [item]}, bright) is None
    assert primary_egg({"detections": [candidate()]}, np.zeros_like(bright)) is None
    assert primary_egg({"detections": [candidate()]}, bright)["class"] == "FERTILE"


def test_presence_latch_records_once_and_rearms_only_after_clear_frames():
    latch = PresenceLatch()
    assert [latch.observe(candidate()) for _ in range(30)].count(True) == 1
    for _ in range(4):
        assert not latch.observe(None)
    assert not latch.observe(candidate())
    for _ in range(5):
        latch.observe(None)
    assert [latch.observe(candidate()) for _ in range(3)] == [False, False, True]


def test_telemetry_flood_is_coalesced_without_losing_optical_events():
    inbox = EventInbox(capacity=32)
    for number in range(10000):
        inbox.put(ControllerEvent("egg", "rx", f"POSITION:{number}"))
    inbox.put(ControllerEvent("egg", "rx", "EVENT:EGG_DETECTED"))
    inbox.put(ControllerEvent("egg", "connection", "DISCONNECTED"))
    assert [inbox.get_nowait().value for _ in range(3)] == [
        "POSITION:9999", "EVENT:EGG_DETECTED", "DISCONNECTED"]
    assert inbox.dropped == 0
    with pytest.raises(queue.Empty):
        inbox.get_nowait()
    for number in range(100):
        inbox.put(ControllerEvent("egg", "tx", str(number)))
    assert inbox.dropped == 68


def test_optical_detection_debounce_requires_real_event():
    counter = OpticalCounter()
    assert not counter.feed("STATE:AT_CHAMBER", now=0)
    assert counter.feed("EVENT:EGG_DETECTED", now=1)
    assert not counter.feed("EVENT:EGG_DETECTED", now=1.4)
    assert counter.feed("EVENT:EGG_DETECTED", now=1.7)
    assert counter.count == 2


def test_real_camera_failure_is_reported_without_generated_frames():
    class MissingCapture:
        released = False
        def isOpened(self): return False
        def release(self): self.released = True
    capture = MissingCapture()
    events = queue.Queue()
    camera = RealCamera(0, events, capture_factory=lambda *args: capture)
    camera.start()
    wait_for(lambda: not camera.active)
    assert camera.snapshot()[2] is None
    assert "unavailable" in str(events.get_nowait().value)
    assert capture.released


class TestCamera:
    __test__ = False
    def __init__(self, index, events):
        self.active = False
        self.number = 0
        self.frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
    def start(self): self.active = True
    def stop(self): self.active = False
    def snapshot(self):
        self.number += 1
        return self.number, time.monotonic(), self.frame, 30


@pytest.mark.parametrize("confidence,action,state", [
    (0.95, "ACCEPT", "FERTILE"), (0.7, "MANUAL_REVIEW", "MANUAL_REVIEW")])
def test_detection_is_committed_to_wal_before_sorting(tmp_path, confidence, action, state):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    calls = []
    original = db.record_scan
    def record(*args):
        calls.append(threading.current_thread().name)
        return original(*args)
    db.record_scan = record
    class Engine:
        def predict(self, frame):
            return {"detections": [candidate(confidence)], "inference_ms": 12, "engine": "ONNX test"}
    worker = VisionWorker(queue.Queue(), engine_factory=Engine, store_factory=lambda: db,
                          camera_factory=TestCamera)
    try:
        worker.start()
        wait_for(lambda: worker.last_scan is not None and worker.snapshot() is not None)
        saved = db.get_uncommitted_scans()
        assert len(saved) == 1 and saved[0]["routing_action"] == action
        assert worker.counts[state] == 1
        assert calls == ["OvaLens-Prototype-Vision"]
        with db._get_connection() as connection:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        if action == "MANUAL_REVIEW":
            with pytest.raises(ValueError, match="manually"):
                worker.routable_scan()
        else:
            scan = worker.routable_scan()
            assert scan["scan_id"] == saved[0]["scan_id"]
            worker.mark_routed(scan["scan_id"])
            with pytest.raises(ValueError, match="already"):
                worker.routable_scan()
        time.sleep(0.15)
        assert len(db.get_uncommitted_scans()) == 1
    finally:
        worker.stop()
        wait_for(lambda: not worker.active)


def test_storage_failure_holds_detection_for_manual_review():
    events = queue.Queue()
    class Engine:
        def predict(self, frame):
            return {"detections": [candidate()], "inference_ms": 10, "engine": "ONNX test"}
    class BrokenStore:
        def create_session(self, *args): pass
        def record_scan(self, *args): raise OSError("Disk unavailable")
        def complete_session(self, *args): pass
    worker = VisionWorker(events, engine_factory=Engine, store_factory=BrokenStore,
                          camera_factory=TestCamera)
    worker.start()
    wait_for(lambda: not worker.active)
    assert worker.last_scan is None
    assert any(event.kind == "error" and "Disk unavailable" in str(event.value)
               for event in list(events.queue))
    with pytest.raises(ValueError):
        worker.routable_scan()


def test_sorting_refuses_stale_or_mismatched_live_detection():
    worker = VisionWorker(queue.Queue())
    now = time.monotonic()
    worker.last_scan = {"scan_id": "stored", "state": "FERTILE", "final_class": "FERTILE",
                        "recorded_at": now, "sequence_number": 1}
    worker.latest = {"timestamp": now - 1, "state": "FERTILE"}
    with pytest.raises(ValueError, match="fresh"):
        worker.routable_scan()
    worker.latest = {"timestamp": now, "state": "NO_EGG"}
    with pytest.raises(ValueError, match="manually"):
        worker.routable_scan()
    worker.latest = {"timestamp": now, "state": "FERTILE"}
    worker.last_scan["recorded_at"] = now - 11
    with pytest.raises(ValueError, match="stale"):
        worker.routable_scan()
    worker.last_scan["recorded_at"] = now
    worker.stop()
    with pytest.raises(ValueError, match="fresh"):
        worker.routable_scan()


def test_cycle_inspection_suspends_travel_and_rearms_after_station_stop(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "cycle.db"))
    class Engine:
        def predict(self, frame):
            return {"detections": [candidate()], "inference_ms": 10, "engine": "ONNX test"}
    worker = VisionWorker(queue.Queue(), engine_factory=Engine, store_factory=lambda: db,
                          camera_factory=TestCamera)
    try:
        worker.start()
        worker.suspend_inspection()
        time.sleep(0.15)
        assert worker.snapshot() is None and worker.last_scan is None
        assert db.get_uncommitted_scans() == []
        after = time.monotonic() + 0.15
        inspection = worker.begin_inspection(after)
        time.sleep(0.05)
        assert worker.last_scan is None
        wait_for(lambda: worker.last_scan is not None and worker.snapshot() is not None)
        first = worker.routable_scan()
        assert first["inspection_id"] == inspection and first["captured_at"] >= after
        worker.suspend_inspection()
        wait_for(lambda: worker.snapshot() is None)
        time.sleep(0.15)
        assert len(db.get_uncommitted_scans()) == 1
        # The fixture remains in view: explicit stationary inspection, rather
        # than old presence or a traveling frame, rearms the next cycle.
        next_id = worker.begin_inspection(time.monotonic())
        wait_for(lambda: worker.last_scan is not None and worker.snapshot() is not None)
        assert worker.routable_scan()["inspection_id"] == next_id
        assert worker.last_scan["scan_id"] != first["scan_id"]
        assert len(db.get_uncommitted_scans()) == 2
    finally:
        worker.stop()
        wait_for(lambda: not worker.active)
