"""TASK-NEW-EDGE-CONTROL-01: hardware-free transport, camera and cycle contracts."""
from concurrent.futures import Future
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import queue
import sys
import threading
import time

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.camera import CameraGrabber
from src.core.settings import EdgeSettings, SettingsStore
from src.core.inference_worker import InferenceWorker
from src.core.sorting_cycle import SortingCycle, StableEvidence, ReviewRequired
from src.core.station import EdgeStation
from src.db.local_db import LocalDatabaseManager
from src.iot.dual_board import BoardLink, BoardState


class WireBoard:
    """Byte-oriented v2 board simulator used by the actual transport worker."""
    def __init__(self, role="CONVEYOR", silent_commands=False):
        self.role = role
        self.silent_commands = silent_commands
        self.inbox = queue.Queue()
        self.writes = []
        self.last_id = 0
        self.fault = "STARTUP_ACK_REQUIRED"
        self.closed = False
        self.emit(f"BOOT:{role}_V2\nREADY:{role}_V2:PROTOCOL=2\n" + self.report())

    def emit(self, text):
        self.inbox.put(text.encode("ascii"))

    def report(self, ident=None):
        prefix = f"ID:{ident}:" if ident else ""
        fields = ["IR_CAPABLE:1", "IR_ACTIVE:0", "REFERENCE_VALID:1", "POSITION:0", "BUSY:0",
                  f"FAULT:{self.fault}", f"LAST_ID:{self.last_id}", "STATE:IDLE"]
        return "".join(prefix + item + "\n" for item in fields)

    def write(self, data):
        text = data.decode().strip()
        self.writes.append(text)
        if text == "HELLO":
            self.emit(f"READY:{self.role}_V2:PROTOCOL=2\n")
        elif text == "STATUS":
            self.emit(self.report())
        elif text.startswith("@"):
            ident, command = text[1:].split(" ", 1)
            self.last_id = int(ident)
            if not self.silent_commands:
                self.fault = "NONE"
                self.emit(f"ID:{ident}:OK:FAULT_ACKNOWLEDGED\n" + self.report(ident))
        return len(data)

    def read(self, count):
        try:
            return self.inbox.get(timeout=.01)
        except queue.Empty:
            return b""

    def close(self):
        self.closed = True


def test_actual_serial_worker_identifies_without_motion_and_times_out_without_retry():
    wire = WireBoard(silent_commands=True)
    failures = []
    link = BoardLink("CONVEYOR", "COM5", failures.append, lambda *a, **k: wire)
    link.start()
    try:
        deadline = time.monotonic() + 1
        while not link._status_complete and time.monotonic() < deadline:
            time.sleep(.01)
        assert link._status_complete
        assert not any(text.startswith("@") for text in wire.writes)
        future = link.command("ACK_FAULT", timeout=.1)
        with pytest.raises(RuntimeError, match="timeout"):
            future.result(1)
        link._thread.join(1)
        assert wire.closed and failures
        assert len([text for text in wire.writes if text.startswith("@")]) == 1
        assert "ESTOP" in wire.writes
    finally:
        link.stop()


def test_stop_signal_bypasses_pending_motion_and_cancels_queue():
    wire = WireBoard(silent_commands=True)
    link = BoardLink("CONVEYOR", "COM5", serial_factory=lambda *a, **k: wire)
    link.start()
    try:
        deadline = time.monotonic() + 1
        while not link._status_complete and time.monotonic() < deadline:
            time.sleep(.01)
        pending = link.command("INDEX:100", timeout=3)
        queued = link.command("INDEX:200", timeout=3)
        link.halt()
        with pytest.raises(RuntimeError):
            pending.result(1)
        with pytest.raises(RuntimeError):
            queued.result(1)
        assert "@2 INDEX:200" not in wire.writes
        assert "ESTOP" in wire.writes
    finally:
        link.stop()


def classification(kind="FERTILE", confidence=.92):
    return {"engine": "ONNX Runtime (CPU)", "final_class": kind, "confidence": confidence,
            "inference_ms": 8, "detections": [] if kind is None else [
                {"class": kind, "confidence": confidence, "bbox": [.5, .5, .4, .5]}]}


def test_saved_settings_roundtrip_and_corrupt_defaults_fail_explicitly(tmp_path):
    store = SettingsStore(tmp_path / "defaults.json")
    settings = EdgeSettings(conveyor_port="COM5", servo_port="COM7")
    settings.camera.exposure, settings.camera.auto_exposure = -6, .25
    store.save(settings)
    assert store.load().snapshot() == settings.snapshot()
    assert not list(tmp_path.glob("*.tmp"))
    store.path.write_text('{"version":99}', encoding="utf-8")
    with pytest.raises(ValueError, match="Saved settings"):
        store.load()


@pytest.mark.parametrize("group,name,value", [
    ("detection", "sort_confidence", .69), ("detection", "confidence", float("nan")),
    ("calibration", "direction", 0), ("calibration", "holder_steps", True),
    ("calibration", "gate_clearance_steps", 500), ("camera", "fps", 0)])
def test_invalid_settings_are_rejected(group, name, value):
    values = EdgeSettings().snapshot()
    values[group][name] = value
    with pytest.raises(ValueError):
        EdgeSettings.from_dict(values)


def test_evidence_requires_three_distinct_frames_over_300ms():
    evidence = StableEvidence(.85)
    assert not evidence.add(1, classification())
    assert not evidence.add(1.1, classification())
    assert not evidence.add(1.2, classification())
    assert evidence.add(1.31, classification(confidence=.88))
    assert evidence.result()["confidence"] == .88


@pytest.mark.parametrize("change", ["low", "class", "position", "multiple", "invalid", "repeat"])
def test_conflicting_evidence_requires_review(change):
    evidence = StableEvidence(.85)
    evidence.add(1, classification())
    result = classification()
    stamp = 1.2
    if change == "low":
        result["confidence"] = .7
    elif change == "class":
        result = classification("INFERTILE")
    elif change == "position":
        result["detections"][0]["bbox"][0] = .9
    elif change == "multiple":
        result["detections"].append(deepcopy(result["detections"][0]))
    elif change == "invalid":
        result["confidence"] = float("nan")
    else:
        stamp = 1
    with pytest.raises(ReviewRequired):
        evidence.add(stamp, result)


def test_camera_properties_are_applied_on_owner_and_readback_is_not_assumed(monkeypatch):
    class Capture:
        def __init__(self, *args):
            self.values, self.owners = {}, set()
        def isOpened(self):
            return True
        def getBackendName(self):
            return "DSHOW"
        def set(self, prop, value):
            import cv2
            self.owners.add(threading.get_ident())
            if prop == cv2.CAP_PROP_FOCUS:
                return False
            self.values[prop] = value
            return True
        def get(self, prop):
            return self.values.get(prop, 0)
        def read(self):
            time.sleep(.005)
            return True, np.zeros((120, 160, 3), dtype=np.uint8)
        def release(self):
            self.owners.add(threading.get_ident())
    capture = Capture()
    monkeypatch.setattr("src.core.camera.cv2.VideoCapture", lambda *args: capture)
    camera = CameraGrabber()
    settings = EdgeSettings().camera
    settings.exposure, settings.focus = -5, 10
    try:
        report = camera.apply_settings(settings)
        assert report["properties"]["exposure"]["status"] == "verified readback"
        assert report["properties"]["focus"]["status"] == "rejected / unsupported"
        deadline = time.monotonic() + 2
        while camera.snapshot() is None and time.monotonic() < deadline:
            time.sleep(.01)
        frame = camera.snapshot()
        assert frame is not None and frame.settings_revision == report["revision"]
        assert threading.get_ident() not in capture.owners
    finally:
        camera.stop()


def test_transport_role_reset_correlation_and_priority_stop():
    failures = []
    link = BoardLink("CONVEYOR", "COM5", failures.append)
    link.state.connected = True
    link._receive("READY:CONVEYOR_V2:PROTOCOL=2", 1)
    link._receive("LAST_ID:12", 1)
    link._receive("STATE:FAULT", 1)
    assert link._next_id == 13 and link._status_complete
    future = Future()
    link._pending = [13, "INDEX:100", 5, future, False]
    link._receive("ID:12:OK:MOVE_DONE", 2)
    link._receive("ID:12:STATE:IDLE", 2)
    assert not future.done()
    link._receive("ID:13:EVENT:IR:90", 2)
    link._receive("ID:13:OK:MOVE_DONE", 2)
    assert not future.done()  # Wait for position and final STATE, not only DONE.
    link._receive("ID:13:POSITION:100", 2)
    link._receive("ID:13:STATE:IDLE", 2)
    assert future.result()["POSITION"] == "100"
    assert "IR_EVENT" in future.result()
    for _ in range(8):
        link._queue.put_nowait(("JOG:1", 2, Future()))
    link.halt()
    assert link._halt.is_set()
    link._receive("BOOT:CONVEYOR_V2", 3)
    assert failures and "reset" in failures[-1]
    assert link._queue.empty()
    wrong = BoardLink("SERVO", "COM7", failures.append)
    wrong._receive("READY:CONVEYOR_V2:PROTOCOL=2", 1)
    assert "mismatch" in failures[-1]


def test_camera_restores_defaults_at_start_and_switches_device_without_reapplying_old_profile(monkeypatch):
    opened = []
    class Capture:
        def __init__(self, index, *args):
            opened.append(index)
            self.values = {}
        def isOpened(self):
            return True
        def getBackendName(self):
            return "DSHOW"
        def set(self, prop, value):
            self.values[prop] = value
            return True
        def get(self, prop):
            return self.values.get(prop, 0)
        def read(self):
            time.sleep(.005)
            return True, np.zeros((120, 160, 3), dtype=np.uint8)
        def release(self):
            pass
    monkeypatch.setattr("src.core.camera.cv2.VideoCapture", Capture)
    camera = CameraGrabber()
    camera.initial_settings = EdgeSettings().camera
    camera.initial_settings.exposure = -6
    camera.start()
    try:
        deadline = time.monotonic() + 2
        while camera.snapshot() is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert camera.snapshot() is not None
        assert camera.property_report["exposure"]["actual"] == -6
        settings = EdgeSettings().camera
        settings.index, settings.exposure = 1, -3
        report = camera.apply_settings(settings)
        assert report["identity"] == "opencv:1:DSHOW"
        assert report["properties"]["exposure"]["actual"] == -3
        assert opened == [0, 1] and camera.camera_index == 1
    finally:
        camera.stop()


def test_scheduler_serializes_engine_and_prioritizes_capture():
    entered, release = threading.Event(), threading.Event()
    order = []
    def predict(value):
        order.append(value)
        if value == "preview1":
            entered.set()
            assert release.wait(2)
        return {"value": value}
    worker = InferenceWorker(SimpleNamespace(predict=predict))
    worker.start()
    results = []
    first = threading.Thread(target=lambda: results.append(worker.predict("preview1")))
    third = threading.Thread(target=lambda: results.append(worker.predict("capture", capture=True)))
    try:
        first.start()
        assert entered.wait(1)
        preview_future = Future()
        worker._preview.put_nowait(("preview2", preview_future))
        third.start()
        deadline = time.monotonic() + 1
        while worker._captures.empty() and time.monotonic() < deadline:
            time.sleep(.005)
        release.set()
        for thread in (first, third):
            thread.join(2)
        assert order == ["preview1", "capture"]
        assert preview_future.cancelled()
        assert len(results) == 2
    finally:
        release.set()
        worker.stop()


class FakeBoard:
    def __init__(self, role, trace):
        self.role, self.trace = role, trace
        self.position = 0
    def snapshot(self):
        return BoardState(self.role, True, True, {"FAULT": "NONE", "POSITION": str(self.position), "BUSY": "0"})
    def command(self, text, timeout=3):
        self.trace.append((self.role, text))
        reply = {}
        if text.startswith("INDEX:"):
            self.position += int(text.split(":")[1])
            reply["POSITION"] = str(self.position)
            # Holder 2 is empty. Chamber coordinates are multiples of 1000.
            if self.position % 1000 == 0 and abs(self.position) != 2000:
                reply["IR_EVENT"] = "IR"
        future = Future()
        future.set_result(reply)
        return future


def cycle_fixture(tmp_path, results):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    trace = []
    boards = SimpleNamespace(failure="", conveyor=FakeBoard("CONVEYOR", trace),
        servo=FakeBoard("SERVO", trace), halt=lambda: trace.append(("BOTH", "STOP")), require_ready=lambda: None)
    settings = EdgeSettings()
    settings.calibration.sorter_steps = 1500  # Non-integer holder spacing is supported.
    settings.calibration.settle_ms = settings.calibration.passage_ms = 0
    cycle = SortingCycle(boards, SimpleNamespace(), SimpleNamespace(), db, settings, "d", "s", "b", 2, "operator")
    sequence = iter(results)
    cycle._capture = lambda: (next(sequence), {"test": True})
    return cycle, db, trace


@pytest.mark.parametrize("direction", [1, -1])
def test_multi_holder_gaps_durable_evidence_and_correct_gate_order(tmp_path, direction):
    cycle, db, trace = cycle_fixture(tmp_path, [classification(), classification(None), classification("INFERTILE")])
    cycle.settings.calibration.direction = direction
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    assert cycle.count == cycle.routed == 2
    assert [(role, command) for role, command in trace if command.startswith("SORT:")] == [
        ("SERVO", "SORT:FERTILE"), ("SERVO", "SORT:INFERTILE")]
    fertile = trace.index(("SERVO", "SORT:FERTILE"))
    assert trace[fertile + 1][0] == "CONVEYOR"
    rows = db.get_uncommitted_scans()
    assert len(rows) == 2  # Ordinary offline operation keeps both records.
    assert json.loads(rows[0]["evidence_json"])["holder"] == 1
    assert json.loads(rows[1]["evidence_json"])["holder"] == 3
    assert db.load_machine_state("d")["state"] == "COMPLETE"


def test_storage_failure_never_releases_classified_holder(tmp_path, monkeypatch):
    cycle, db, trace = cycle_fixture(tmp_path, [classification()])
    def failed(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(db, "record_scan", failed)
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert len([c for _, c in trace if c.startswith("INDEX:")]) == 1
    assert not any(c.startswith("SORT:") for _, c in trace)
    assert trace[-1] == ("BOTH", "STOP")


def test_ir_camera_conflict_holds_until_operator_resolution(tmp_path):
    cycle, db, trace = cycle_fixture(tmp_path, [classification(None), classification(None), classification("INFERTILE")])
    reasons = []
    def review(reason, holder):
        reasons.append(reason)
        return "FERTILE"
    cycle._review = review
    cycle._run()
    assert reasons == ["IR and camera evidence disagree"]
    assert db.get_uncommitted_scans()[0]["routing_action"] == "MANUAL_REVIEW"


def test_motion_timeout_and_wrong_position_force_recovery(tmp_path):
    cycle, db, trace = cycle_fixture(tmp_path, [classification()])
    original = cycle.boards.conveyor.command
    def wrong(text, timeout=3):
        future = original(text, timeout)
        reply = future.result()
        reply["POSITION"] = "123"
        return future
    cycle.boards.conveyor.command = wrong
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert not db.get_uncommitted_scans()
    assert db.load_machine_state("d")["state"] == "RECOVERY_REQUIRED"


def test_restart_preserves_journal_without_connecting_or_restoring_motion(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    journal = {"state": "MOVE_IN_FLIGHT", "session_id": "old", "holders": [{"number": 1, "stage": "SAVED"}]}
    db.save_machine_state("d", journal)
    station = EdgeStation(SimpleNamespace(), SimpleNamespace(), db, "d", SettingsStore(tmp_path / "defaults.json"))
    assert station.recovery == journal
    assert station.boards is None and not station.calibrated and not station.active
    with pytest.raises(RuntimeError, match="Validate calibration"):
        station.start_cycle("b", 10, "operator")


def test_settings_lock_and_camera_change_confirmation(tmp_path):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    calls = []
    camera = SimpleNamespace(apply_settings=lambda settings: calls.append(settings))
    station = EdgeStation(camera, SimpleNamespace(), db, "d", SettingsStore(tmp_path / "defaults.json"))
    station.cycle = SimpleNamespace(active=True)
    with pytest.raises(RuntimeError, match="Stop sorting"):
        station.apply(EdgeSettings())
    assert not calls
    station.cycle = None
    settings = EdgeSettings()
    settings.camera.index = 1
    station.calibrated = True
    with pytest.raises(ValueError, match="Confirm"):
        station.apply(settings)
    assert not station.calibrated and not calls


def test_camera_failure_stops_motion_before_dispatch(tmp_path):
    cycle, db, trace = cycle_fixture(tmp_path, [classification()])
    cycle.camera = SimpleNamespace(is_running=False, last_error="camera disconnected")
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert not any(command.startswith("INDEX:") for _, command in trace)
    assert trace[-1] == ("BOTH", "STOP")
