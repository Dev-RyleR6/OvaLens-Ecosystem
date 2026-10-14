"""TASK-NEW-EDGE-3BOARD-01: role discovery, real workers and full routing cycles."""
from concurrent.futures import Future
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import queue
import sys
import threading
import time
import uuid
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.camera import CameraGrabber, CameraFrame
from src.core.settings import EdgeSettings, SettingsStore
from src.core.station import EdgeStation
from src.core.sorting_cycle import ReviewRequired
from src.core.three_board_cycle import ThreeBoardCycle
from src.core.inference import InferenceEngine
from src.core.inference_worker import InferenceWorker
from src.db.local_db import LocalDatabaseManager
from src.iot.dual_board import BoardLink, BoardState
from src.iot.three_board import ThreeBoardController, discover_boards, ROLES
from src.sync.sync_worker import BackgroundSyncWorker


def prediction(kind="FERTILE", confidence=.94):
    return {"engine": "ONNX Runtime (CPU)", "final_class": kind, "confidence": confidence,
            "inference_ms": 8, "detections": [] if kind is None else [
                {"class": kind, "confidence": confidence, "bbox": [.5, .5, .4, .5]}]}


class Wire:
    """Byte-oriented v3 simulator exercised by the real background BoardLink."""
    def __init__(self, role, *, version=3, silent=False):
        self.role, self.version, self.silent = role, version, silent
        self.inbox, self.writes, self.closed = queue.Queue(), [], False
        self.fault, self.last_id = "STARTUP_ACK_REQUIRED", 0
        self.reference, self.light = "0", "0"
        self.angle, self.neutral = "90", "90"
        self.emit(f"BOOT:{role}_V{version}\nREADY:{role}_V{version}:PROTOCOL={version}\n" + self.report())

    def emit(self, text):
        self.inbox.put(text.encode("ascii"))

    def report(self, ident=None):
        prefix = f"ID:{ident}:" if ident is not None else ""
        fields = ["POSITION:0", "SENSOR:0", "EGG_SEQ:0", "PAUSED:1", "BUSY:0", f"LIGHT:{self.light}", f"ANGLE:{self.angle}",
                  f"REFERENCE_VALID:{self.reference}", f"FAULT:{self.fault}", f"LAST_ID:{self.last_id}", "STATE:WAITING"]
        return "".join(prefix + field + "\n" for field in fields)

    def write(self, data):
        text = data.decode().strip()
        self.writes.append(text)
        if text == "HELLO":
            self.emit(f"READY:{self.role}_V{self.version}:PROTOCOL={self.version}\n" + self.report())
        elif text == "PING":
            self.emit(f"PONG:{self.role}\n")
        elif text == "STATUS":
            self.emit(self.report())
        elif text.startswith("@") and not self.silent:
            ident, command = text[1:].split(" ", 1)
            self.last_id = int(ident)
            ok = "OK:STATUS"
            if command == "ACK_FAULT":
                self.fault, ok = "NONE", "OK:FAULT_ACKNOWLEDGED"
            elif command == "SETHOME":
                self.reference, ok = "1", "OK:HOME_SET"
            elif command in {"LIGHT_ON", "LIGHT_OFF"}:
                self.light, ok = str(int(command == "LIGHT_ON")), "OK:" + command
            elif command.startswith("SET_NEUTRAL:"):
                self.neutral = command.split(":", 1)[1]
            elif command == "RESET":
                self.angle = self.neutral
            self.emit(f"ID:{ident}:{ok}\n" + self.report(int(ident)))
        return len(data)

    def read(self, count):
        try:
            return self.inbox.get(timeout=.005)
        except queue.Empty:
            return b""

    def close(self):
        self.closed = True


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        time.sleep(.005)
    assert predicate()


def test_discovery_uses_ping_roles_and_version_without_motion():
    wires = {port: Wire(role) for port, role in zip(("COM9", "COM2", "COM6"), ROLES)}
    result = discover_boards(list(reversed(wires)), lambda port, *a, **k: wires[port], timeout=.1)
    assert result == dict(zip(ROLES, wires))
    assert all(wire.closed and set(wire.writes) <= {"PING", "HELLO"} for wire in wires.values())


def test_discovery_rejects_missing_wrong_version_and_duplicate_roles():
    with pytest.raises(RuntimeError, match="Missing v3"):
        discover_boards(["a"], lambda *a, **k: Wire("CONVEYOR", version=2), timeout=.03)
    with pytest.raises(ValueError, match="Duplicate"):
        discover_boards(["a", "b"], lambda *a, **k: Wire("CONVEYOR"), timeout=.03)


def test_real_three_workers_require_explicit_ack_and_stop_every_board_on_reset():
    wires = {port: Wire(role) for port, role in zip(("a", "b", "c"), ROLES)}
    boards = ThreeBoardController("a", "b", "c", lambda port, *a, **k: wires[port])
    boards.start()
    try:
        wait_for(lambda: all(link._status_complete for link in boards.links))
        with pytest.raises(RuntimeError, match="acknowledgement"):
            boards.require_ready()
        assert not any(request.startswith("@") for wire in wires.values() for request in wire.writes)
        for link in boards.links:
            link.command("ACK_FAULT").result(1)
        boards.conveyor.command("SETHOME").result(1)
        boards.require_ready()
        wires["c"].emit("BOOT:LIGHT_CONTROLLER_V3\n")
        wait_for(lambda: bool(boards.failure))
        wait_for(lambda: all("ESTOP" in wire.writes for wire in wires.values()))
        assert "reset" in boards.failure
        assert not any("RESUME" in request for wire in wires.values() for request in wire.writes)
    finally:
        boards.stop()


def test_v3_reports_are_atomic_correlated_and_events_are_bounded():
    link = BoardLink("EGG_CONTROLLER", "b", protocol=3)
    link.state.connected = True
    link._receive("READY:EGG_CONTROLLER_V3:PROTOCOL=3", 1)
    link._receive("EGG_SEQ:1", 1)
    assert "EGG_SEQ" not in link.snapshot().telemetry
    link._receive("FAULT:NONE", 1)
    link._receive("STATE:HOLDING", 1)
    assert link.snapshot().telemetry["EGG_SEQ"] == "1"
    future = Future()
    link._pending = [8, "STATUS", 10, future, False]
    for line in ("ID:7:OK:STATUS", "ID:7:EGG_SEQ:2", "ID:7:STATE:WAITING"):
        link._receive(line, 2)
    assert not future.done() and link.snapshot().telemetry["EGG_SEQ"] == "1"
    for line in ("ID:8:OK:STATUS", "ID:8:EGG_SEQ:1", "ID:8:STATE:HOLDING"):
        link._receive(line, 2)
    assert future.result()["STATE"] == "HOLDING"
    for index in range(65):
        link._receive(f"EVENT:EGG_DETECTED:{index}", 3)
    assert "overflow" in link.snapshot().error


@pytest.mark.parametrize("fault", ["low", "missing", "duplicate", "case"])
def test_three_board_configuration_and_saved_profile_migration(tmp_path, fault):
    settings = EdgeSettings.three_board()
    assert (settings.camera.index, settings.calibration.fertile_angle, settings.calibration.speed_us) == (0, 180, 3000)
    settings.conveyor_port, settings.servo_port, settings.light_port = "COM1", "COM2", "COM3"
    if fault == "low":
        settings.detection.sort_confidence = .69
    elif fault == "missing":
        settings.light_port = ""
        with pytest.raises(ValueError):
            ThreeBoardController(settings.conveyor_port, settings.servo_port, settings.light_port)
        return
    else:
        settings.light_port = "COM1" if fault == "duplicate" else "com1"
    with pytest.raises(ValueError):
        settings.validate()


def test_old_saved_settings_keep_two_board_profile_and_new_stations_use_handoff(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.load().rig_profile == "three_v3"
    old = EdgeSettings().snapshot()
    for key in ("rig_profile", "light_port"):
        old.pop(key)
    for key in ("hold_ms", "buffer_drain", "jam_timeout_s"):
        old["calibration"].pop(key)
    store.path.write_text(json.dumps(old), encoding="utf-8")
    restored = store.load()
    assert restored.rig_profile == "dual_v2" and restored.calibration.fertile_angle == 60


@pytest.mark.parametrize("names,shape", [
    ("{0: 'INF', 1: 'FER'}", [1, 6, 8400]), ("{}", [1, 6, 8400]),
    ("{0: 'FER', 1: 'INF', 2: 'ABNORMAL'}", [1, 7, 8400]),
    ("{0: 'FER', 1: 'INF'}", [1, 300, 6])])
def test_model_contract_rejects_swapped_unknown_or_incompatible_detector(tmp_path, names, shape):
    engine = InferenceEngine.__new__(InferenceEngine)
    engine.imgsz, engine.onnx_path, engine.model_contract_verified = 640, str(tmp_path / "model.onnx"), False
    engine.onnx_session = SimpleNamespace(
        get_inputs=lambda: [SimpleNamespace(shape=[1, 3, 640, 640], type="tensor(float16)")],
        get_outputs=lambda: [SimpleNamespace(shape=shape)],
        get_modelmeta=lambda: SimpleNamespace(custom_metadata_map={"names": names}))
    with pytest.raises(ValueError):
        engine._validate_onnx_contract()
    assert not engine.model_contract_verified


def test_verified_model_identity_records_actual_precision_and_hash(tmp_path):
    engine = InferenceEngine.__new__(InferenceEngine)
    engine.imgsz, engine.onnx_path = 640, str(tmp_path / "model.onnx")
    Path(engine.onnx_path).write_bytes(b"test model bytes")
    engine.onnx_session = SimpleNamespace(
        get_inputs=lambda: [SimpleNamespace(shape=[1, 3, 640, 640], type="tensor(float)")],
        get_outputs=lambda: [SimpleNamespace(shape=[1, 6, 8400])],
        get_modelmeta=lambda: SimpleNamespace(custom_metadata_map={"names": "{0: 'FER', 1: 'INF'}"}))
    engine._validate_onnx_contract()
    assert engine.model_contract_verified and engine.model_identity["input_type"] == "tensor(float)"
    assert len(engine.model_identity["sha256"]) == 64


def test_lost_ack_never_replays_a_command_and_forces_stop():
    wire = Wire("CONVEYOR", silent=True)
    link = BoardLink("CONVEYOR", "a", serial_factory=lambda *a, **k: wire, protocol=3)
    link.start()
    try:
        wait_for(lambda: link._status_complete)
        pending = link.command("ADVANCE:100", timeout=.1)
        with pytest.raises(RuntimeError, match="timeout"):
            pending.result(2)
        wait_for(lambda: wire.closed)
        assert sum("ADVANCE:100" in request for request in wire.writes) == 1
        assert "ESTOP" in wire.writes
    finally:
        link.stop()


class FakeLink:
    def __init__(self, role, rig):
        self.role, self.rig, self.events = role, rig, queue.Queue()
        self.values = {"FAULT": "NONE", "BUSY": "0", "POSITION": "0", "PAUSED": "0", "SENSOR": "0",
                       "EGG_SEQ": "0", "STATE": "WAITING", "REFERENCE_VALID": "1", "LIGHT": "0", "ANGLE": "90"}

    def snapshot(self):
        return BoardState(self.role, True, True, dict(self.values))

    def command(self, command, timeout=3):
        rig = self.rig
        rig.trace.append((self.role, command, rig.position, rig.db.get_unsynced_count()))
        future = Future()
        try:
            if rig.fail_command == (self.role, command):
                raise RuntimeError("Injected acknowledgement timeout")
            if command.startswith("ADVANCE:"):
                destination = rig.position + int(command.split(":")[1])
                arrivals = [p for p in rig.arrivals if rig.position < p <= destination]
                rig.position = min(arrivals) if arrivals else destination
                self.values["POSITION"] = str(rig.position)
                if arrivals:
                    seq = int(rig.egg.values["EGG_SEQ"]) + 1
                    rig.egg.values.update(EGG_SEQ=str(seq), STATE="HOLDING", SENSOR="1", PAUSED="1")
                    self.values["PAUSED"] = "1"
                    rig.egg.events.put(("EGG_DETECTED", seq))
                    if rig.duplicate:
                        rig.egg.events.put(("EGG_DETECTED", seq))
            elif command.startswith("SORT:") or command == "RESET":
                self.values["ANGLE"] = "180" if command == "SORT:FERTILE" else "120" if command == "SORT:INFERTILE" else "90"
            elif command == "RESUME":
                self.values.update(PAUSED="0", SENSOR="0", STATE="WAITING")
                rig.conveyor.values["PAUSED"] = "0"
                if int(self.values["EGG_SEQ"]):
                    self.events.put(("EGG_CLEARED", int(self.values["EGG_SEQ"])))
            elif command in {"ARM", "PAUSE"}:
                self.values["PAUSED"] = "1"
                rig.conveyor.values["PAUSED"] = "1"
            elif command in {"LIGHT_ON", "LIGHT_OFF"}:
                self.values["LIGHT"] = str(int(command == "LIGHT_ON"))
            future.set_result(dict(self.values))
        except Exception as exc:
            future.set_exception(exc)
        return future


class Rig:
    def __init__(self, db, arrivals):
        self.db, self.arrivals, self.position = db, arrivals, 0
        self.trace, self.failure, self.fail_command, self.duplicate = [], "", None, False
        self.conveyor, self.egg, self.light = [FakeLink(role, self) for role in ROLES]
        self.servo, self.links = self.egg, (self.conveyor, self.egg, self.light)

    def require_ready(self):
        pass

    def halt(self):
        self.trace.append(("ALL", "ESTOP", self.position, self.db.get_unsynced_count()))
        self.egg.values["PAUSED"] = "1"
        self.light.values["LIGHT"] = "0"


def fixture(tmp_path, count=2, arrivals=None):
    db = LocalDatabaseManager(str(tmp_path / "scans.db"))
    boards = Rig(db, arrivals if arrivals is not None else [100 + n * 450 for n in range(count)])
    settings = EdgeSettings.three_board()
    settings.calibration.hold_ms = settings.calibration.settle_ms = 0
    image = np.full((120, 160, 3), 150, dtype=np.uint8)
    camera = SimpleNamespace(last_error=None, is_running=True, is_mock_mode=False, settings_revision=0,
                             snapshot=lambda **k: CameraFrame(1, time.monotonic(), 0, image))
    cycle = ThreeBoardCycle(boards, camera, SimpleNamespace(), db, settings, "station", str(uuid.uuid4()), "batch", count, "operator")
    captures = iter(prediction("FERTILE" if n % 2 == 0 else "INFERTILE") for n in range(count))
    cycle._capture = lambda: (next(captures), {"simulated_evidence": True})
    return cycle, db, boards


def test_fifty_egg_cycle_orders_gates_and_persists_every_decision(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=50)
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    assert cycle.count == cycle.routed == 50
    routes = [(command, position, saved) for role, command, position, saved in rig.trace if command.startswith("SORT:")]
    assert len(routes) == 50
    for index, (command, position, saved) in enumerate(routes):
        assert command == ("SORT:FERTILE" if index % 2 == 0 else "SORT:INFERTILE")
        assert position == rig.arrivals[index] and saved >= index + 1
    assert db.get_unsynced_count() == 50
    assert db.load_machine_state("station")["state"] == "COMPLETE"
    assert rig.egg.values["PAUSED"] == "1" and rig.light.values["LIGHT"] == "0"


def test_next_egg_does_not_overwrite_previous_gate(tmp_path):
    cycle, db, rig = fixture(tmp_path, arrivals=[100, 250])
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert "increase feed spacing" in cycle.status["reason"]
    assert [(command, position) for _, command, position, _ in rig.trace
            if command.startswith("SORT:") or command == "RESET"] == [("SORT:FERTILE", 100)]
    assert cycle.count == 1 and cycle.routed == 0
    pending = db.load_machine_state("station")["pending_capture"]
    assert pending["egg_seq"] == 2 and pending["position"] == 250
    assert rig.egg.values["PAUSED"] == "1"


@pytest.mark.parametrize("failure", ["storage", "duplicate", "lamp", "camera", "overlap", "extra"])
def test_failures_hold_transport_and_preserve_recovery(tmp_path, monkeypatch, failure):
    cycle, db, rig = fixture(tmp_path)
    if failure == "storage":
        monkeypatch.setattr(db, "record_scan", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    elif failure == "duplicate":
        rig.duplicate = True
    elif failure == "lamp":
        rig.fail_command = ("LIGHT_CONTROLLER", "LIGHT_OFF")
    elif failure == "camera":
        cycle.camera.last_error = "unplugged"
    elif failure == "overlap":
        rig.arrivals = [100, 150]
    else:
        cycle.target, rig.arrivals = 1, [100, 250]
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED", cycle.status
    assert rig.trace[-1][1] == "ESTOP"
    assert db.load_machine_state("station")["state"] == "RECOVERY_REQUIRED"
    if failure in {"storage", "duplicate", "camera"}:
        assert not any(command.startswith("SORT:") for _, command, _, _ in rig.trace)


def test_review_controls_wait_for_durable_journal(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1)
    saving, release = threading.Event(), threading.Event()
    checkpoint = cycle._checkpoint
    def blocked_checkpoint(state):
        if state == "MANUAL_REVIEW":
            saving.set()
            assert release.wait(3)
        checkpoint(state)
    def uncertain():
        raise ReviewRequired("Low confidence")
    cycle._checkpoint, cycle._capture = blocked_checkpoint, uncertain
    thread = threading.Thread(target=cycle._run)
    thread.start()
    try:
        assert saving.wait(3)
        assert cycle.status["state"] != "MANUAL_REVIEW"
        with pytest.raises(ValueError, match="No matching manual review"):
            cycle.resolve_review("INFERTILE")
        assert rig.light.values["LIGHT"] == "0"
        release.set()
        wait_for(lambda: cycle.status["state"] == "MANUAL_REVIEW")
        assert db.load_machine_state("station")["pending_capture"]["review_reason"] == "Low confidence"
        cycle.resolve_review("INFERTILE")
        thread.join(3)
        assert cycle.status["state"] == "COMPLETE", cycle.status
    finally:
        release.set()
        cycle.stop()
        thread.join(2)


def test_low_confidence_review_keeps_lamp_off_and_requires_operator(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1)
    def uncertain():
        cycle._last_result = prediction(confidence=.70)
        cycle.review_frame = cycle.camera.snapshot().image
        raise ReviewRequired("Low confidence")
    cycle._capture = uncertain
    thread = threading.Thread(target=cycle._run)
    thread.start()
    try:
        wait_for(lambda: cycle.status["state"] == "MANUAL_REVIEW")
        assert rig.egg.values["PAUSED"] == "1" and rig.light.values["LIGHT"] == "0"
        assert not any(command.startswith("SORT:") for _, command, _, _ in rig.trace)
        assert db.load_machine_state("station")["pending_capture"]["review_reason"] == "Low confidence"
        cycle.resolve_review("INFERTILE")
        thread.join(3)
        assert cycle.status["state"] == "COMPLETE", cycle.status
        row = db.get_uncommitted_scans()[0]
        assert row["routing_action"] == "MANUAL_REVIEW" and row["final_class"] == "INFERTILE"
        assert json.loads(row["evidence_json"])["verification"]["manual_resolution"] == "INFERTILE"
    finally:
        cycle.stop()
        thread.join(2)


@pytest.mark.parametrize("fault", ["wrong_position", "pause_wire", "lost_event"])
def test_cross_board_synchronization_fault_cannot_release_an_egg(tmp_path, fault):
    cycle, db, rig = fixture(tmp_path, count=1)
    original = rig.conveyor.command
    def corrupted(command, timeout=3):
        future = original(command, timeout)
        if command.startswith("ADVANCE:"):
            if fault == "wrong_position":
                replacement = Future()
                replacement.set_result({**future.result(), "POSITION": "-99"})
                return replacement
            if fault == "pause_wire":
                rig.conveyor.values["PAUSED"] = "0"
            if fault == "lost_event":
                rig.egg.events.get_nowait()
        return future
    rig.conveyor.command = corrupted
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert db.get_unsynced_count() == 0
    assert not any(command.startswith("SORT:") for _, command, _, _ in rig.trace)
    assert rig.trace[-1][1] == "ESTOP"


def test_stop_during_review_never_resumes(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1)
    cycle._capture = lambda: (_ for _ in ()).throw(ReviewRequired("Inspect"))
    thread = threading.Thread(target=cycle._run)
    thread.start()
    wait_for(lambda: cycle.status["state"] == "MANUAL_REVIEW")
    resumes = sum(command == "RESUME" for _, command, _, _ in rig.trace)
    cycle.stop()
    thread.join(2)
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert sum(command == "RESUME" for _, command, _, _ in rig.trace) == resumes
    station = EdgeStation(cycle.camera, SimpleNamespace(), db, "station", SettingsStore(tmp_path / "settings.json"))
    assert station.recovery["pending_capture"]["scan_id"] and station.boards is None
    assert not station.calibrated


def test_real_camera_owner_flushes_six_frames_and_saves_image(tmp_path, monkeypatch):
    owners, grabs = set(), []
    class Capture:
        def __init__(self, *args):
            self.properties = {}
        def isOpened(self):
            return True
        def getBackendName(self):
            return "DSHOW"
        def set(self, key, value):
            self.properties[key] = value
            return True
        def grab(self):
            owners.add(threading.get_ident())
            grabs.append(1)
            return True
        def read(self):
            owners.add(threading.get_ident())
            time.sleep(.01)
            return True, np.full((120, 160, 3), 150, dtype=np.uint8)
        def release(self):
            owners.add(threading.get_ident())
    monkeypatch.setattr("src.core.camera.cv2.VideoCapture", Capture)
    cycle, db, rig = fixture(tmp_path, count=1)
    camera = CameraGrabber()
    camera.start()
    try:
        wait_for(lambda: camera.snapshot() is not None)
        cycle.camera = camera
        cycle.inference = SimpleNamespace(predict=lambda *a, **k: prediction())
        cycle.pending_capture = {"scan_id": str(uuid.uuid4())}
        cycle._origin, cycle._last_egg_seq = 0, 1
        rig.conveyor.values.update(PAUSED="1")
        rig.egg.values.update(STATE="HOLDING", PAUSED="1", EGG_SEQ="1")
        result, evidence = ThreeBoardCycle._capture(cycle)
        assert result["final_class"] == "FERTILE" and evidence["frames"] == 3 and evidence["span_ms"] >= 300
        assert len(grabs) == 6 and threading.get_ident() not in owners
        assert Path(cycle.pending_capture["image_path"]).is_file()
        assert not list(Path(cycle.pending_capture["image_path"]).parent.glob("*.tmp"))
    finally:
        camera.stop()


def test_offline_cycle_replays_after_lost_ack_without_duplicate_ids(tmp_path, monkeypatch):
    cycle, db, rig = fixture(tmp_path, count=50)
    cycle._run()
    assert cycle.status["state"] == "COMPLETE"
    # This fixture bypasses camera capture; attach saved evidence for full replay.
    for row in db.get_uncommitted_scans():
        path = db.save_scan_image(row["scan_id"], np.zeros((20, 20, 3), dtype=np.uint8))
        with db._get_connection() as conn:
            conn.execute("UPDATE local_scans SET image_path = ? WHERE scan_id = ?", (path, row["scan_id"]))
    worker = BackgroundSyncWorker(db, api_key="test")
    stored, phase = set(), {"offline": True, "lose_ack": True}
    def post(url, **kwargs):
        if phase["offline"]:
            raise OSError("network down")
        if url.endswith("/sessions"):
            return SimpleNamespace(status_code=200, json=lambda: kwargs["json"])
        if url.endswith("/upload-image"):
            import hashlib
            scan_id = kwargs["data"]["scan_id"]
            data = kwargs["files"]["file"][1]
            return SimpleNamespace(status_code=200, json=lambda: {"status": "success", "scan_id": scan_id,
                "image_url": f"/storage/{scan_id}.jpg", "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data)})
        incoming = {row["scan_id"] for row in kwargs["json"]["scans"]}
        duplicates = len(stored & incoming)
        stored.update(incoming)
        if phase["lose_ack"]:
            phase["lose_ack"] = False
            raise OSError("server committed, acknowledgement lost")
        return SimpleNamespace(status_code=200, json=lambda: {"status": "success", "total_received": len(incoming),
            "synced_count": len(incoming) - duplicates, "duplicates_ignored": duplicates})
    monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
    monkeypatch.setattr("src.sync.sync_worker.requests.put", lambda *a, **k:
        SimpleNamespace(status_code=200, json=lambda: db.get_session_stats(cycle.session_id)))
    monkeypatch.setattr("src.sync.sync_worker.requests.get", lambda *a, **k: SimpleNamespace(status_code=200))
    worker._perform_sync()
    assert db.get_unsynced_count() == 50
    phase["offline"] = False
    worker._perform_sync()
    assert worker.last_error and "OSError" in worker.last_error
    assert len(stored) == db.get_unsynced_count() == 50
    worker._perform_sync()
    assert db.get_unsynced_count() == 45 and not db.get_uncommitted_scans()
    for _ in range(9):
        worker._perform_sync()
    assert db.get_unsynced_count() == 0 and len(stored) == 50


def test_fifty_eggs_through_real_capture_inference_workers_and_wal(tmp_path, monkeypatch):
    """Synthetic camera/model adapters, actual workers/evidence/storage/coordinator."""
    class Capture:
        def __init__(self, *args):
            self.grabs = self.reads = 0
        def isOpened(self):
            return True
        def getBackendName(self):
            return "DSHOW"
        def set(self, *args):
            return True
        def grab(self):
            self.grabs += 1
            return True
        def read(self):
            time.sleep(.01)
            self.reads += 1
            return True, np.full((120, 160, 3), self.reads % 240, dtype=np.uint8)
        def release(self):
            pass
    capture = Capture()
    monkeypatch.setattr("src.core.camera.cv2.VideoCapture", lambda *args: capture)
    cycle, db, rig = fixture(tmp_path, count=50)
    camera = CameraGrabber()
    calls = []
    def infer(frame):
        assert rig.conveyor.values["BUSY"] == "0" and rig.conveyor.values["PAUSED"] == "1"
        assert rig.egg.values["STATE"] == "HOLDING" and rig.light.values["LIGHT"] == "1"
        value = int(frame[0, 0, 0])
        calls.append((int(rig.egg.values["EGG_SEQ"]), value))
        return {**prediction("FERTILE" if int(rig.egg.values["EGG_SEQ"]) % 2 else "INFERTILE"),
                "captured_pixel": value}
    engine = SimpleNamespace(engine_type="ONNX Runtime (simulation adapter)",
        model_identity={"simulated": True}, predict=infer)
    original_command = FakeLink.command
    def command(link, text, timeout=3):
        if text == "RESUME" or text.startswith("ADVANCE:"):
            assert cycle.capture_view is None
        return original_command(link, text, timeout)
    monkeypatch.setattr(FakeLink, "command", command)
    worker = InferenceWorker(engine)
    camera.start()
    worker.start()
    try:
        wait_for(lambda: camera.snapshot() is not None)
        cycle.camera, cycle.inference = camera, worker
        cycle._capture = ThreeBoardCycle._capture.__get__(cycle)
        cycle._run()
        assert cycle.status["state"] == "COMPLETE", cycle.status
        assert cycle.count == cycle.routed == 50 and capture.grabs == 300
        assert len(calls) == 150  # Three predictions per egg, none during motion.
        rows = db.get_uncommitted_scans()
        assert len(rows) == 50 and len({row["scan_id"] for row in rows}) == 50
        for index, row in enumerate(rows):
            assert row["final_class"] == ("FERTILE" if index % 2 == 0 else "INFERTILE")
            evidence = json.loads(row["evidence_json"])
            assert evidence["verification"]["frames"] == 3
            assert evidence["verification"]["span_ms"] >= 300
            import cv2
            image = cv2.imread(row["image_path"])
            assert int(image[0, 0, 0]) == evidence["capture"]["prediction"]["captured_pixel"]
            assert evidence["capture"]["frame"]["sequence"] > 0
        assert not worker.busy
    finally:
        cycle.stop()
        worker.stop()
        camera.stop()
