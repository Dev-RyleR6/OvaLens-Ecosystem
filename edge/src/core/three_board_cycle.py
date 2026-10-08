"""Sensor arrivals and position events for the three-board candling rig.

The gate is positioned before releasing each classified egg and retained until
its calibrated exit. A new arrival cannot change an earlier egg's gate preset.
"""
from dataclasses import asdict
import heapq
import math
import queue
import time
import uuid
from .capture_view import CaptureView
from .sorting_cycle import SortingCycle, Holder, ReviewRequired


def finite_evidence(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: finite_evidence(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_evidence(item) for item in value]
    return value


class ThreeBoardCycle(SortingCycle):
    allow_empty_capture = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.review_frame = None
        self.pending_capture = None
        self._last_egg_seq = 0
        self._detected_events = set()
        self._gate_holder = None
        self._search_deadline = None

    def _checkpoint(self, state):
        self.db.save_machine_state(self.device_id, finite_evidence({
            "state": state, "rig_profile": "three_v3", "session_id": self.session_id,
            "batch_id": self.batch_id, "travel": self.travel, "count": self.count,
            "routed": self.routed, "egg_seq": self._last_egg_seq,
            "holders": [asdict(h) for h in self.holders], "pending_capture": self.pending_capture,
            "settings": self.settings.snapshot()}))

    def _health(self):
        if self._stop.is_set():
            raise RuntimeError("Operator stopped; inspect eggs before recovery")
        if self.boards.failure:
            raise RuntimeError(self.boards.failure)
        if self.camera.last_error or not self.camera.is_running or self.camera.snapshot(copy=False) is None:
            raise RuntimeError("Camera unavailable or stale; inspect before restarting")
        for link in self.boards.links:
            state = link.snapshot()
            if not state.connected or not state.identified or state.error or state.telemetry.get("FAULT") != "NONE":
                raise RuntimeError(f"{link.role} is unavailable or faulted")

    def _capture(self):
        k = self.settings.calibration
        self.clear_capture_view()
        self._capture_health(lit=False)
        self._state("LIGHTING", holder=self.count + 1)
        lamp = self._command(self.boards.light, "LIGHT_ON")
        if lamp.get("LIGHT") != "1":
            raise RuntimeError("Candling lamp did not confirm ON")
        self._state("STABILIZING", holder=self.count + 1)
        self._delay(k.settle_ms / 1000)
        after, revision = time.monotonic(), self.camera.settings_revision
        frame = self.camera.capture_fresh(k.buffer_drain, timeout=3)
        self._capture_health()
        if frame.settings_revision != revision:
            raise RuntimeError("Camera settings changed during capture")
        self.review_frame = frame.image
        self.pending_capture["image_path"] = self.db.save_scan_image(self.pending_capture["scan_id"], frame.image)
        view = CaptureView.create(frame, {})
        self.pending_capture["frame"] = view.identity()
        with self._view_lock:
            if self._stop.is_set():
                raise RuntimeError("Operator stopped during capture")
            self.capture_view = view
        self._checkpoint("CAPTURED")
        self._state("CLASSIFYING", holder=self.count + 1)
        try:
            result, evidence = self._collect_evidence(after, revision, frame)
            return result, {**evidence, "buffer_drain": k.buffer_drain}
        finally:
            view = self.capture_view
            if view is not None:
                # Persist the same image as the final prediction, including review cases.
                self.review_frame = view.frame.image
                self.pending_capture["image_path"] = self.db.save_scan_image(
                    self.pending_capture["scan_id"], view.frame.image)
                self.pending_capture["prediction"] = finite_evidence(view.result)
                self.pending_capture["frame"] = view.identity()

    def _capture_health(self, lit=True):
        super()._capture_health()
        egg = self.boards.egg.snapshot().telemetry
        conveyor = self.boards.conveyor.snapshot().telemetry
        if (egg.get("STATE") != "HOLDING" or egg.get("PAUSED") != "1"
                or int(egg["EGG_SEQ"]) != self._last_egg_seq or conveyor.get("PAUSED") != "1"):
            raise RuntimeError("Egg hold or hardware pause changed during capture")
        if lit and self.boards.light.snapshot().telemetry.get("LIGHT") != "1":
            raise RuntimeError("Candling lamp changed during capture")

    def _lamp_off(self):
        reply = self._command(self.boards.light, "LIGHT_OFF")
        if reply.get("LIGHT") != "0":
            raise RuntimeError("Candling lamp did not confirm OFF")

    def _review(self, reason, holder):
        # Human review may outlast the independent 15-second lamp watchdog.
        self._lamp_off()
        self.pending_capture["review_reason"] = reason
        return super()._review(reason, holder)

    def _events(self):
        while True:
            try:
                kind, seq = self.boards.egg.events.get_nowait()
            except queue.Empty:
                break
            if kind == "EGG_DETECTED":
                if seq <= self._last_egg_seq or seq in self._detected_events:
                    raise RuntimeError("Duplicate or stale egg detection; reconcile physical eggs")
                self._detected_events.add(seq)
            elif kind == "EGG_CLEARED":
                if seq > self._last_egg_seq:
                    raise RuntimeError("Clear event arrived before its capture")
            else:
                raise RuntimeError("Unexpected gate event during position-controlled routing")

    def _advance(self, destination):
        self.clear_capture_view()
        k = self.settings.calibration
        delta = destination - self.travel
        if not 0 < delta <= 100000:
            raise RuntimeError("Invalid position event order or movement bound")
        self._checkpoint("MOVE_IN_FLIGHT")
        timeout = max(3, delta * 2 * k.speed_us / 1000000 + 2)
        if self.count < self.target and self._search_deadline is not None:
            timeout = min(timeout, max(.01, self._search_deadline - time.monotonic()))
        reply = self._command(self.boards.conveyor, f"ADVANCE:{delta * k.direction}", timeout)
        actual = (int(reply["POSITION"]) - self._origin) * k.direction
        if actual < self.travel or actual > destination:
            raise RuntimeError("Conveyor position disagrees with commanded travel")
        self.travel = actual
        egg = self._command(self.boards.egg, "STATUS")
        conveyor = self._command(self.boards.conveyor, "STATUS")
        if int(conveyor["POSITION"]) != int(reply["POSITION"]) or conveyor.get("BUSY") != "0":
            raise RuntimeError("Conveyor moved after reporting completion")
        self._events()
        seq = int(egg["EGG_SEQ"])
        detected = egg.get("STATE") == "HOLDING" and egg.get("PAUSED") == "1"
        if detected:
            if conveyor.get("PAUSED") != "1" or seq != self._last_egg_seq + 1 or self._detected_events != {seq}:
                raise RuntimeError("Egg sequence or hardware pause disagreement")
            self._last_egg_seq = seq
            self._detected_events.clear()
        elif actual != destination or seq != self._last_egg_seq or conveyor.get("PAUSED") != "0" or self._detected_events:
            raise RuntimeError("Unexpected pause or lost sensor event")
        self._checkpoint("STOPPED")
        return detected

    def _handle_egg(self, events):
        if self.count >= self.target:
            raise RuntimeError("Additional egg during batch drain; inspect before recovery")
        holder = Holder(self._last_egg_seq, self.travel, scan_id=str(uuid.uuid4()))
        self.holders.append(holder)
        self.pending_capture = {"scan_id": holder.scan_id, "egg_seq": self._last_egg_seq,
                                "position": self.travel}
        self._last_result = {}
        self._checkpoint("EGG_HELD")
        if self._gate_holder is not None:
            raise RuntimeError("Next egg arrived before the previous egg cleared the gate; increase feed spacing")
        manual = False
        try:
            result, verification = self._capture()
        except (ReviewRequired, TimeoutError) as exc:
            decision = self._review(str(exc), holder)
            result = dict(self._last_result)
            result["final_class"] = None if decision == "EMPTY" else decision
            value = result.get("confidence", 0)
            result["confidence"] = value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1 else 0.0
            verification = {"manual_resolution": decision, "reason": str(exc)}
            manual = True
        self._health()
        if result.get("final_class") is None:
            holder.stage = "EMPTY_CONFIRMED"
            self.holders.remove(holder)
        else:
            holder.final_class = result["final_class"]
            action = "MANUAL_REVIEW" if manual else "ACCEPT" if holder.final_class == "FERTILE" else "REJECT"
            self._state("SAVING", holder=holder.number)
            self.db.record_scan(holder.scan_id, self.session_id, self.batch_id, self.count + 1,
                holder.final_class, result["confidence"], int(result.get("inference_ms", 0)), action,
                finite_evidence(result.get("detections", [])), image_path=self.pending_capture.get("image_path"),
                evidence={"settings": self.settings.snapshot(), "holder": holder.number,
                          "model": getattr(getattr(self.inference, "engine", None), "model_identity", {}),
                          "verification": verification, "capture": finite_evidence(self.pending_capture)})
            self.count += 1
            holder.stage = "SAVED"
            self.latest_result = {**result, "holder": holder.number, "scan_id": holder.scan_id, "routing_action": action}
            k = self.settings.calibration
            self._checkpoint("SAVED")
            self._position_gate(holder)
            heapq.heappush(events, (self.travel + k.sorter_steps + k.gate_clearance_steps, 0, "clear", holder.number))
            self._state("DISPLAYING", holder=holder.number)
            self._delay(k.hold_ms / 1000)
        self._lamp_off()
        self.pending_capture = None
        self.review_frame = None
        self._checkpoint("CAPTURE_COMPLETE")

    def _position_gate(self, holder):
        """Complete the servo stroke while the detected egg still holds the belt."""
        self._capture_health(lit=False)
        self._state("ROUTING", "Positioning sorting gate; belt held", holder=holder.number)
        self._checkpoint("SERVO_IN_FLIGHT")
        reply = self._command(self.boards.egg, f"SORT:{holder.final_class}")
        angle = (self.settings.calibration.fertile_angle if holder.final_class == "FERTILE"
                 else self.settings.calibration.infertile_angle)
        if reply.get("BUSY") != "0" or reply.get("ANGLE") != str(angle):
            raise RuntimeError("Sorting servo did not confirm the required gate position")
        self._capture_health(lit=False)
        self._gate_holder, holder.stage = holder.number, "ROUTE_COMMANDED"
        self._checkpoint("GATE_READY")

    def _clear_gate(self, events):
        while events and events[0][0] <= self.travel:
            position, _, kind, number = heapq.heappop(events)
            if position != self.travel or kind != "clear":
                raise RuntimeError("A gate boundary was crossed without a stopped routing decision")
            holder = next(h for h in self.holders if h.number == number)
            if self._gate_holder != number or holder.stage != "ROUTE_COMMANDED":
                raise RuntimeError("Egg crossed an unprepared sorting gate")
            self._state("ROUTING", holder=number)
            self._command(self.boards.egg, "RESET")
            self._gate_holder = None
            holder.stage = "PASSAGE_ESTIMATED"
            self.routed += 1
            self.holders.remove(holder)
            self._checkpoint("GATE_READY")

    def _run(self):
        started = last_arrival = time.monotonic()
        k, events = self.settings.calibration, []
        try:
            self._health()
            self._origin = int(self.boards.conveyor.snapshot().telemetry["POSITION"])
            self._last_egg_seq = int(self.boards.egg.snapshot().telemetry["EGG_SEQ"])
            # Stale queued events are not permission to process an egg after reconnect.
            while not self.boards.egg.events.empty():
                self.boards.egg.events.get_nowait()
            self.db.create_session(self.session_id, self.batch_id, self.device_id, "DAY_10", self.operator)
            self._checkpoint("STARTED")
            self._command(self.boards.egg, "ARM")
            self.clear_capture_view()
            self._command(self.boards.egg, "RESUME")
            while self.count < self.target or events:
                self._health()
                if self._gate_holder is None and self.count < self.target and time.monotonic() - last_arrival >= k.jam_timeout_s:
                    raise RuntimeError("No egg arrival before the search deadline")
                destination = min(self.travel + k.holder_steps, events[0][0]) if events else self.travel + k.holder_steps
                self._search_deadline = last_arrival + k.jam_timeout_s if self._gate_holder is None else None
                if self._gate_holder is not None:
                    self._state("INDEXING", "Egg travelling to gate; wait before feeding", holder=self._gate_holder)
                else:
                    self._state("SEARCHING", "Gate clear; feed next egg", holder=self.count + 1)
                detected = self._advance(destination)
                # At an exact exit/arrival boundary, finish the previous egg first.
                routed_before = self.routed
                self._clear_gate(events)
                if self.routed != routed_before:
                    last_arrival = time.monotonic()
                if detected:
                    self._handle_egg(events)
                    last_arrival = time.monotonic()
                if self.boards.egg.snapshot().telemetry.get("PAUSED") == "1":
                    self.clear_capture_view()
                    self._command(self.boards.egg, "RESUME")
            final_egg = self._command(self.boards.egg, "STATUS")
            if final_egg.get("SENSOR") != "0" or final_egg.get("STATE") != "WAITING":
                raise RuntimeError("Chamber did not clear after the final egg")
            self._command(self.boards.egg, "PAUSE")
            self._lamp_off()
            self.db.complete_session(self.session_id)
            self._checkpoint("COMPLETE")
            self._state("COMPLETE", "Gate passage estimated from issued steps; inspect output trays")
        except Exception as exc:
            self.clear_capture_view()
            self.boards.halt()
            self._state("RECOVERY_REQUIRED", str(exc))
            try:
                self._checkpoint("RECOVERY_REQUIRED")
            except Exception:
                pass
        finally:
            self.metrics["cycle_ms"] = (time.monotonic() - started) * 1000
