"""Feedback-driven, non-blocking stepper/camera/servo prototype cycle."""

from dataclasses import dataclass
import time

from .controller import integer


@dataclass(frozen=True)
class CycleSettings:
    camera_steps: int = 1000
    resume_steps: int = 1000
    step_delay: int = 1800
    neutral_angle: int = 90
    block_angle: int = 30
    fertile_angle: int = 30
    infertile_angle: int = 90
    settle_ms: int = 300
    servo_settle_ms: int = 300
    detection_timeout: int = 15
    mode: str = "Detect & block"

    @property
    def gate_steps(self):
        return self.resume_steps // 2

    @property
    def clearance_steps(self):
        return self.resume_steps - self.gate_steps

    def validate(self):
        integer(self.camera_steps, 1, 100000, "Camera travel")
        integer(self.resume_steps, 2, 100000, "Resumed travel")
        integer(self.step_delay, 200, 5000, "Step delay")
        for name in ("neutral_angle", "block_angle", "fertile_angle", "infertile_angle"):
            integer(getattr(self, name), 0, 180, name.replace("_", " "))
        integer(self.settle_ms, 0, 5000, "Camera settling time")
        integer(self.servo_settle_ms, 0, 5000, "Servo settling time")
        integer(self.detection_timeout, 1, 120, "Detection timeout")
        if self.mode not in {"Classify & sort", "Detect & block"}:
            raise ValueError("Choose classification or detection blocking mode.")
        if self.mode == "Detect & block" and self.block_angle == self.neutral_angle:
            raise ValueError("Blocking angle must differ from neutral.")
        return self


class AutomaticCycle:
    """Tick from the GUI; all actual USB/camera/storage work stays on workers.

    Motion is segmented because the deployed legacy board has no shared
    actuator scheduling protocol. No elapsed-time guess completes a move.
    """

    RUNNING = {"INITIALIZING", "TO_CAMERA", "INSPECTING", "TO_GATE",
               "BLOCKING", "CLEARING", "RESETTING"}

    def __init__(self, rig, vision, clock=time.monotonic):
        self.rig, self.vision, self.clock = rig, vision, clock
        self.state = "IDLE"
        self.message = "Ready for an automatic cycle"
        self.completed = 0
        self.settings = None
        self.deadline = 0
        self.next_status = 0
        self.position = None
        self.target = None
        self.feedback = {}
        self.servo_angle = None
        self.expected_angle = None
        self.move_sent = False
        self.servo_sent = False
        self.inspection_id = None
        self.scan = None
        self.inspection_after = 0
        self.servo_ack_at = None

    @property
    def active(self):
        return self.state in self.RUNNING

    def start(self, settings):
        if self.active:
            raise ValueError("An automatic cycle is already running.")
        settings.validate()
        if not all(link.ready and not link.simulated for link in self.rig.links.values()):
            raise ValueError("Connect the real stepper on COM5 and servo on COM7 first.")
        if not self.vision.active:
            raise ValueError("Start the real camera before starting an automatic cycle.")
        self.settings, self.completed, self.scan = settings, 0, None
        self.feedback = {}
        self.position = self.servo_angle = None
        self.move_sent = self.servo_sent = False
        self.servo_ack_at = None
        self.expected_angle = settings.neutral_angle
        self._phase("INITIALIZING", "Checking camera readiness, stepper idle and servo neutral",
                    max(5, settings.detection_timeout) + settings.servo_settle_ms / 1000)
        try:
            self.vision.suspend_inspection()
            self.rig.links["egg"].send_many([f"SPEED:{settings.step_delay}", "STATUS"])
            self.rig.links["servo"].send_many([
                f"SET_FERTILE:{settings.fertile_angle}", f"SET_INFERTILE:{settings.infertile_angle}",
                f"SERVO:{settings.neutral_angle}", "STATUS"])
        except ValueError as exc:
            self.fail(str(exc))

    def _phase(self, state, message, timeout):
        self.state, self.message = state, message
        self.deadline = self.clock() + timeout
        self.next_status = self.clock() + 0.15

    def _move(self, steps, state, message):
        self.vision.suspend_inspection()
        self.target = self.position + steps
        self.feedback = {}
        self.move_sent = False
        # Two signal edges per step plus generous USB/acceleration overhead.
        timeout = max(5, steps * self.settings.step_delay * 2 / 1_000_000 + 5)
        self._phase(state, message, timeout)
        self.rig.links["egg"].send(f"JOG:{steps}")

    def _servo(self, command, angle, state, message):
        self.expected_angle, self.servo_angle, self.servo_sent = angle, None, False
        self.servo_ack_at = None
        self._phase(state, message, 5 + self.settings.servo_settle_ms / 1000)
        self.rig.links["servo"].send(command)

    def event(self, event):
        if not self.active:
            return
        if event.kind == "error" or (event.kind == "connection" and
                                      event.value in {"DISCONNECTED", "DISCONNECTING"}):
            self.fail(f"{event.role} controller: {event.value}")
            return
        if event.kind == "tx":
            if event.role == "egg" and event.value.startswith("JOG:"):
                self.move_sent = True
                self.feedback = {}
            elif event.role == "egg" and event.value == "STATUS" and self.state == "INITIALIZING":
                self.move_sent = True
            elif event.role == "servo" and event.value.startswith(("SERVO:", "SORT:")):
                self.servo_sent = True
                self.servo_angle = None
            return
        if event.kind != "rx":
            return
        if event.value.startswith(("ERROR:", "NACK:")):
            self.fail(f"{event.role} board: {event.value}")
            return
        key, _, value = event.value.partition(":")
        if event.role == "egg" and self.move_sent and key in {"POSITION", "BUSY", "AUTO"}:
            try:
                self.feedback[key] = int(value)
            except ValueError:
                self.fail("Invalid stepper position/status feedback")
            if key == "POSITION":
                self.position = self.feedback.get("POSITION")
        elif event.role == "servo" and self.servo_sent and key == "ANGLE":
            try:
                self.servo_angle = int(value)
            except ValueError:
                self.fail("Invalid servo angle feedback")

    def _idle_at(self, target=None):
        return (self.move_sent and self.feedback.get("BUSY") == 0 and
                self.feedback.get("AUTO") == 0 and "POSITION" in self.feedback and
                (target is None or self.feedback["POSITION"] == target))

    def tick(self):
        if not self.active:
            return
        try:
            if not all(link.ready and not link.simulated for link in self.rig.links.values()):
                self.fail("Controller connection lost")
                return
            if not self.vision.active:
                self.fail("Camera detection stopped")
                return
            now = self.clock()
            if self.servo_angle == self.expected_angle and self.servo_ack_at is None:
                self.servo_ack_at = now
            servo_ready = (self.servo_ack_at is not None and
                           now - self.servo_ack_at >= self.settings.servo_settle_ms / 1000)
            if now > self.deadline:
                self.fail(f"Timeout during {self.state.replace('_', ' ').lower()}")
                return
            if now >= self.next_status:
                self.rig.links["egg"].send("STATUS")
                if self.state in {"INITIALIZING", "BLOCKING", "RESETTING"}:
                    self.rig.links["servo"].send("STATUS")
                self.next_status = now + 0.15
            if self.state == "INITIALIZING":
                if self.feedback.get("BUSY") == 1 or self.feedback.get("AUTO") == 1:
                    self.fail("Stepper must be idle before starting the cycle")
                elif self._idle_at() and servo_ready and self.vision.ready:
                    self._move(self.settings.camera_steps, "TO_CAMERA", "Moving to camera")
            elif self.state == "TO_CAMERA" and self._idle_at(self.target):
                self.inspection_after = now + self.settings.settle_ms / 1000
                self.inspection_id = self.vision.begin_inspection(self.inspection_after)
                self._phase("INSPECTING", "Stopped at camera · waiting for a recorded egg",
                            self.settings.detection_timeout + self.settings.settle_ms / 1000)
            elif self.state == "INSPECTING":
                latest = self.vision.snapshot()
                if latest and latest.get("inspection_id") == self.inspection_id and latest["timestamp"] >= self.inspection_after:
                    if latest["state"] == "MANUAL_REVIEW":
                        self.fail("Low confidence egg · inspect manually")
                        return
                    try:
                        scan = self.vision.routable_scan()
                    except ValueError:
                        return
                    if scan.get("inspection_id") != self.inspection_id or scan.get("captured_at", 0) < self.inspection_after:
                        return
                    self.scan = scan
                    self.vision.mark_routed(scan["scan_id"])
                    self._move(self.settings.gate_steps, "TO_GATE", "Egg recorded · moving to halfway servo trigger")
            elif self.state == "TO_GATE" and self._idle_at(self.target):
                if self.settings.mode == "Detect & block":
                    command, angle = f"SERVO:{self.settings.block_angle}", self.settings.block_angle
                else:
                    cls = self.scan["final_class"]
                    command = f"SORT:{cls}"
                    angle = self.settings.fertile_angle if cls == "FERTILE" else self.settings.infertile_angle
                self._servo(command, angle, "BLOCKING", "Halfway through resumed travel · activating servo gate")
            elif self.state == "BLOCKING" and servo_ready:
                self._move(self.settings.clearance_steps, "CLEARING", "Servo held · stepper moving past gate")
            elif self.state == "CLEARING" and self._idle_at(self.target):
                self._servo(f"SERVO:{self.settings.neutral_angle}", self.settings.neutral_angle,
                            "RESETTING", "Cleared gate · resetting servo")
            elif self.state == "RESETTING" and servo_ready:
                self.completed += 1
                self._move(self.settings.camera_steps, "TO_CAMERA", "Starting next egg · moving to camera")
        except (ValueError, RuntimeError) as exc:
            self.fail(str(exc))

    def fail(self, reason):
        self.state, self.message = "MANUAL_REVIEW", reason
        self.vision.suspend_inspection()
        try:
            self.rig.stop()
        except ValueError as exc:
            self.message += f" · {exc}"

    def stop(self):
        self.state, self.message = "STOPPED", "Cycle stopped · stepper returns home, servo resets"
        self.vision.suspend_inspection()
        self.rig.stop()
