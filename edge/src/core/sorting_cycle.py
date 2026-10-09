"""Position-event coordinator for multiple holders; no Tk or HTTP work here."""
from dataclasses import asdict, dataclass
from enum import Enum
import heapq
import math
import threading
import time
import uuid
from .capture_view import CaptureView


class ReviewRequired(RuntimeError):
    pass


class CycleState(str, Enum):
    READY = "READY"
    SEARCHING = "SEARCHING"
    LIGHTING = "LIGHTING"
    STABILIZING = "STABILIZING"
    DISPLAYING = "DISPLAYING"
    INDEXING = "INDEXING"
    CLASSIFYING = "CLASSIFYING"
    SAVING = "SAVING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    ROUTING = "ROUTING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    COMPLETE = "COMPLETE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


def box_iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    intersection = max(0, min(ax + aw / 2, bx + bw / 2) - max(ax - aw / 2, bx - bw / 2)) * max(
        0, min(ay + ah / 2, by + bh / 2) - max(ay - ah / 2, by - bh / 2))
    return intersection / max(1e-9, aw * ah + bw * bh - intersection)


class StableEvidence:
    """Fail closed on class/position disagreement or nonfinite model output."""
    def __init__(self, threshold):
        self.threshold = threshold
        self.samples = []

    def add(self, stamp, result):
        detections = result.get("detections", [])
        if not str(result.get("engine", "")).startswith("ONNX"):
            raise ReviewRequired("Real ONNX inference is required")
        if not detections and result.get("final_class") is None:
            if result.get("error_code") not in (None, "EGG_NOT_CONFIRMED"):
                raise ReviewRequired("Inference failed")
            kind, bbox = "EMPTY", None
        else:
            if len(detections) != 1:
                raise ReviewRequired("Multiple or ambiguous eggs in the camera zone")
            kind = result.get("final_class")
            bbox = detections[0].get("bbox", [])
            confidence = result.get("confidence", 0)
            if (kind not in {"FERTILE", "INFERTILE"} or type(confidence) not in (int, float)
                    or not math.isfinite(confidence) or not self.threshold <= confidence <= 1):
                raise ReviewRequired("Classification confidence requires inspection")
            detection = detections[0]
            detection_confidence = detection.get("confidence", 0)
            if (detection.get("class") != kind or type(detection_confidence) not in (int, float)
                    or not math.isfinite(detection_confidence) or not self.threshold <= detection_confidence <= 1):
                raise ReviewRequired("Detection and classification evidence disagree")
            if (len(bbox) != 4 or not all(type(v) in (int, float) and math.isfinite(v) for v in bbox)
                    or not all(0 <= v <= 1 for v in bbox) or bbox[2] <= 0 or bbox[3] <= 0
                    or not .65 <= bbox[2] / bbox[3] <= 1.45
                    or abs(bbox[0] - .5) > .15 or abs(bbox[1] - .5) > .15):
                raise ReviewRequired("Egg position or geometry requires inspection")
        if self.samples:
            previous = self.samples[-1]
            if stamp <= previous[0]:
                raise ReviewRequired("Repeated or out-of-order capture")
            if previous[1] != kind or (bbox and box_iou(previous[2], bbox) < .6):
                raise ReviewRequired("Class or egg position changed during capture")
        self.samples.append((stamp, kind, bbox, result))
        return len(self.samples) >= 3 and stamp - self.samples[0][0] >= .3

    def result(self):
        result = dict(self.samples[-1][3])
        if self.samples[-1][1] != "EMPTY":
            result["confidence"] = min(s[3]["confidence"] for s in self.samples)
        return result


@dataclass
class Holder:
    number: int
    chamber_position: int
    final_class: str | None = None
    scan_id: str | None = None
    stage: str = "CAPTURE_PENDING"


class SortingCycle:
    allow_empty_capture = True

    def __init__(self, boards, camera, inference, db, settings, device_id, session_id,
                 batch_id, target, operator):
        self.boards, self.camera, self.inference, self.db = boards, camera, inference, db
        self.settings = type(settings).from_dict(settings.snapshot())
        self.device_id, self.session_id, self.batch_id = device_id, session_id, batch_id
        self.target, self.operator = target, operator
        self.holders = []
        self.count = 0
        self.routed = 0
        self.travel = 0
        self.status = {"state": "READY", "reason": "", "holder": 0}
        self.metrics = {"capture_age_ms": 0.0, "cycle_ms": 0.0}
        self.latest_result = None
        self.capture_view = None
        self._view_lock = threading.Lock()
        self._stop = threading.Event()
        self._decision = threading.Event()
        self._resolution = None
        self._thread = None

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    def _state(self, state, reason="", holder=0):
        self.status = {"state": CycleState(state).value, "reason": reason, "holder": holder,
                       "count": self.count, "routed": self.routed}

    def _checkpoint(self, state):
        self.db.save_machine_state(self.device_id, {
            "state": state, "session_id": self.session_id, "batch_id": self.batch_id,
            "travel": self.travel, "count": self.count, "routed": self.routed,
            "holders": [asdict(h) for h in self.holders], "settings": self.settings.snapshot()})

    def start(self):
        if self.active:
            raise RuntimeError("Sorting is already running")
        self.settings.validate()
        self.boards.require_ready()
        if self.camera.is_mock_mode or self.camera.snapshot() is None:
            raise RuntimeError("A fresh real camera frame is required")
        self._thread = threading.Thread(target=self._run, daemon=True, name="OvaLens-SortingCycle")
        self._thread.start()

    def stop(self):
        with self._view_lock:
            self._stop.set()
            self.capture_view = None
        self._decision.set()
        self.boards.halt()

    def resolve_review(self, classification):
        if self.status["state"] != "MANUAL_REVIEW" or classification not in {"FERTILE", "INFERTILE", "EMPTY"}:
            raise ValueError("No matching manual review")
        if self._decision.is_set():
            raise ValueError("Review decision already submitted")
        self._resolution = classification
        self._decision.set()

    def _health(self):
        if self._stop.is_set():
            raise RuntimeError("Operator stopped; inspect holders before recovery")
        if self.boards.failure:
            raise RuntimeError(self.boards.failure)
        if getattr(self.camera, "last_error", None) or not getattr(self.camera, "is_running", True):
            raise RuntimeError("Camera failed; inspect before restarting")
        snapshot = getattr(self.camera, "snapshot", None)
        if callable(snapshot) and snapshot(copy=False) is None:
            raise RuntimeError("Camera frame is stale; conveyor stopped")
        for link in (self.boards.conveyor, self.boards.servo):
            state = link.snapshot()
            if (not state.connected or not state.identified or state.error
                    or state.telemetry.get("FAULT") != "NONE"):
                raise RuntimeError(f"{link.role} is unavailable or faulted")

    def _wait(self, future, timeout):
        deadline = time.monotonic() + timeout
        while not future.done():
            self._health()
            if time.monotonic() >= deadline:
                raise RuntimeError("Command deadline exceeded")
            self._stop.wait(.01)
        self._health()
        return future.result()

    def _command(self, link, command, timeout=3):
        self._health()
        return self._wait(link.command(command, timeout), timeout + .2)

    def _delay(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._health()
            self._stop.wait(min(.02, max(0, deadline - time.monotonic())))

    def _move(self, destination, chamber=False):
        self.clear_capture_view()
        k = self.settings.calibration
        delta = destination - self.travel
        if delta < -k.position_tolerance_steps:
            raise RuntimeError("Position events are out of order")
        if delta <= 0:
            return False
        if delta > 100000:
            raise RuntimeError("Movement exceeds firmware index limit")
        self._checkpoint("MOVE_IN_FLIGHT")
        timeout = max(3, delta * 2 * k.speed_us / 1000000 + 2)
        reply = self._command(self.boards.conveyor, f"INDEX:{delta * k.direction}", timeout)
        actual = (int(reply["POSITION"]) - self._origin) * k.direction
        ir = "IR_EVENT" in reply
        if abs(actual - destination) > (k.position_tolerance_steps if chamber else 0):
            raise RuntimeError("Unexpected IR stop or position disagreement")
        if ir and not chamber:
            raise RuntimeError("IR event outside the calibrated chamber arrival")
        self.travel = actual
        self._checkpoint("STOPPED")
        return ir

    def _capture(self):
        k = self.settings.calibration
        self._delay(k.settle_ms / 1000)
        after = time.monotonic()
        return self._collect_evidence(after, self.camera.settings_revision)

    def clear_capture_view(self):
        with self._view_lock:
            self.capture_view = None

    def _capture_health(self):
        self._health()
        state = self.boards.conveyor.snapshot().telemetry
        expected = self._origin + self.travel * self.settings.calibration.direction
        if state.get("BUSY") != "0" or int(state["POSITION"]) != expected:
            raise RuntimeError("Conveyor is not stationary at the capture position")

    def _collect_evidence(self, after, revision, frame=None):
        try:
            return self._collect_stopped_evidence(after, revision, frame)
        except (ReviewRequired, TimeoutError):
            raise  # Keep the paired snapshot available for inspection.
        except Exception:
            self.clear_capture_view()
            raise

    def _collect_stopped_evidence(self, after, revision, frame):
        """Sample fresh frames at 150ms intervals, with no preview inference work."""
        deadline = time.monotonic() + 2
        evidence = StableEvidence(self.settings.detection.sort_confidence)
        last_sequence = -1
        next_stamp = after
        while time.monotonic() < deadline:
            self._capture_health()
            if frame is None:
                frame = self.camera.snapshot(copy=False)
            if (frame is None or frame.sequence == last_sequence
                    or frame.captured_at <= after or frame.captured_at < next_stamp):
                self._stop.wait(.01)
                frame = None
                continue
            if frame.settings_revision != revision:
                raise RuntimeError("Camera settings changed during sorting")
            last_sequence = frame.sequence
            self.metrics["capture_age_ms"] = (time.monotonic() - frame.captured_at) * 1000
            remaining = deadline - time.monotonic()
            result = self.inference.predict(frame.image, timeout=max(.01, remaining), capture=True)
            self._capture_health()  # A late result cannot outlive a stop, fault or movement.
            if self.camera.settings_revision != revision:
                raise RuntimeError("Camera settings changed during inference")
            if time.monotonic() > deadline:
                raise ReviewRequired("Classification deadline exceeded")
            view = CaptureView.create(frame, result)
            with self._view_lock:
                if self._stop.is_set():
                    raise RuntimeError("Operator stopped during inference")
                self.capture_view = view
            self._last_result = result
            if not self.allow_empty_capture and result.get("final_class") is None:
                raise ReviewRequired("Sensor detected an egg but vision did not confirm it")
            if evidence.add(frame.captured_at, result):
                return evidence.result(), {"frames": len(evidence.samples),
                    "span_ms": (frame.captured_at - evidence.samples[0][0]) * 1000,
                    "settings_revision": revision}
            next_stamp = frame.captured_at + .15
            if len(evidence.samples) == 2:
                next_stamp = max(next_stamp, evidence.samples[0][0] + .3)
            frame = None
        raise ReviewRequired("No stable fresh classification within two seconds")

    def _review(self, reason, holder):
        self._decision.clear()
        self._resolution = None
        self._checkpoint("MANUAL_REVIEW")
        self._state("MANUAL_REVIEW", reason, holder.number)
        while not self._decision.wait(.05):
            self._health()
        self._health()
        return self._resolution

    def _run(self):
        started = time.monotonic()
        k = self.settings.calibration
        try:
            self._origin = int(self.boards.conveyor.snapshot().telemetry["POSITION"])
            self.db.create_session(self.session_id, self.batch_id, self.device_id, "DAY_10", self.operator)
            self._checkpoint("STARTED")
            # Operator aligned the NEXT holder one pitch before the chamber and cleared downstream.
            events = [(k.holder_steps, 1, "capture", 1)]
            by_number = {}
            arrivals = {}
            while events:
                self._health()
                position, _, kind, number = heapq.heappop(events)
                self._state("INDEXING", holder=number)
                chamber_due = kind == "capture" or any(e[0] == position and e[2] == "capture" for e in events)
                ir = self._move(position, chamber=chamber_due)
                if chamber_due and ir:
                    arrivals[position] = True
                if kind == "capture":
                    ir = arrivals.pop(position, False)
                if kind == "capture":
                    holder = Holder(number, position)
                    self.holders.append(holder)
                    by_number[number] = holder
                    self._state("CLASSIFYING", holder=number)
                    self._last_result = {}
                    manual = False
                    try:
                        result, evidence = self._capture()
                        empty = result.get("final_class") is None
                        if empty == ir:
                            raise ReviewRequired("IR and camera evidence disagree")
                    except (ReviewRequired, TimeoutError) as exc:
                        decision = self._review(str(exc), holder)
                        result = dict(self._last_result)
                        result["final_class"] = None if decision == "EMPTY" else decision
                        result["confidence"] = float(result.get("confidence", 0))
                        if not math.isfinite(result["confidence"]) or not 0 <= result["confidence"] <= 1:
                            result["confidence"] = 0.0
                        evidence = {"manual_resolution": decision, "reason": str(exc)}
                        manual = True
                    if result.get("final_class") is None:
                        holder.stage = "EMPTY_CONFIRMED"
                    else:
                        holder.final_class, holder.scan_id = result["final_class"], str(uuid.uuid4())
                        self._state("SAVING", holder=number)
                        action = "MANUAL_REVIEW" if manual else "ACCEPT" if holder.final_class == "FERTILE" else "REJECT"
                        view = self.capture_view
                        image_path = self.db.save_scan_image(holder.scan_id, view.frame.image) if view else None
                        self.db.record_scan(holder.scan_id, self.session_id, self.batch_id, self.count + 1,
                            holder.final_class, result["confidence"], int(result.get("inference_ms", 0)), action,
                            result.get("detections", []), image_path=image_path, evidence={"settings": self.settings.snapshot(),
                            "holder": number, "verification": evidence})
                        self.count += 1
                        self.latest_result = {**result, "scan_id": holder.scan_id, "holder": number,
                                              "routing_action": action}
                        holder.stage = "SAVED"
                        heapq.heappush(events, (position + k.sorter_steps - k.gate_clearance_steps, 0, "route", number))
                        heapq.heappush(events, (position + k.sorter_steps + k.gate_clearance_steps, 2, "clear", number))
                    self._checkpoint("CAPTURED")
                    if holder.stage == "EMPTY_CONFIRMED":
                        self.holders.remove(holder)
                        by_number.pop(number)
                    if self.count < self.target:
                        heapq.heappush(events, (position + k.holder_steps, 1, "capture", number + 1))
                elif kind == "route":
                    holder = by_number[number]
                    if not holder.scan_id or holder.stage != "SAVED":
                        raise RuntimeError("Holder has no durable routing decision")
                    self._state("ROUTING", holder=number)
                    self._checkpoint("SERVO_IN_FLIGHT")
                    self._command(self.boards.servo, f"SORT:{holder.final_class}")
                    holder.stage = "ROUTE_COMMANDED"
                    self._checkpoint("ROUTE_READY")
                else:
                    holder = by_number[number]
                    if holder.stage != "ROUTE_COMMANDED":
                        raise RuntimeError("Holder crossed an unprepared gate")
                    self._delay(k.passage_ms / 1000)
                    self._command(self.boards.servo, "RESET")
                    holder.stage = "PASSAGE_TIMED"  # No independent passage sensor at the gate.
                    self.routed += 1
                    self._checkpoint("PASSAGE_TIMED")
                    self.holders.remove(holder)
                    by_number.pop(number)
            self.db.complete_session(self.session_id)
            self._checkpoint("COMPLETE")
            self._state("COMPLETE", "Gate passage timed; inspect output trays")
        except Exception as exc:
            self.clear_capture_view()
            self.boards.halt()
            self._state("RECOVERY_REQUIRED", str(exc))
            try:
                self._checkpoint("RECOVERY_REQUIRED")
            except Exception:
                pass  # Do not conceal the original storage/hardware fault.
        finally:
            self.metrics["cycle_ms"] = (time.monotonic() - started) * 1000
