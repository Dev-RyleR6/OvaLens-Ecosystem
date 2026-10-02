"""Hardware protocol state transitions for TASK-NEW-FW-CYCLE-01."""

from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from firmware.prototype.controller import ControllerEvent, validate_command
from firmware.prototype.cycle import AutomaticCycle, CycleSettings


class Link:
    ready = True
    simulated = False

    def __init__(self, role):
        self.role, self.commands = role, []

    def send(self, command, priority=False):
        assert self.ready
        self.commands.append(validate_command(self.role, command))

    def send_many(self, commands):
        for command in commands:
            self.send(command)


class Rig:
    def __init__(self):
        self.links = {role: Link(role) for role in ("egg", "servo")}
        self.stops = 0

    def stop(self):
        self.stops += 1
        for role, command in (("egg", "STOP"), ("servo", "RESET")):
            if self.links[role].ready:
                self.links[role].send(command, priority=True)


class Vision:
    active = True
    ready = True

    def __init__(self):
        self.latest = self.scan = None
        self.inspection_id = 0
        self.routed = []
        self.suspended = False

    def suspend_inspection(self):
        self.suspended = True
        self.inspection_id += 1
        self.latest = self.scan = None

    def begin_inspection(self, after):
        self.suspended = False
        self.inspection_id += 1
        self.after = after
        return self.inspection_id

    def snapshot(self):
        return self.latest

    def routable_scan(self):
        if self.scan is None:
            raise ValueError("Not persisted yet")
        return self.scan

    def mark_routed(self, scan_id):
        self.routed.append(scan_id)


@pytest.fixture
def setup_cycle():
    now = [100.0]
    rig, vision = Rig(), Vision()
    cycle = AutomaticCycle(rig, vision, clock=lambda: now[0])
    settings = CycleSettings(settle_ms=0, servo_settle_ms=0)
    cycle.start(settings)
    return cycle, rig, vision, now


def event(cycle, role, value, kind="rx"):
    cycle.event(ControllerEvent(role, kind, value))


def initialize(cycle, position=0):
    event(cycle, "egg", "STATUS", "tx")
    for line in (f"POSITION:{position}", "BUSY:0", "AUTO:0"):
        event(cycle, "egg", line)
    event(cycle, "servo", "SERVO:90", "tx")
    event(cycle, "servo", "ANGLE:90")
    cycle.tick()


def complete_move(cycle):
    event(cycle, "egg", f"JOG:{cycle.target - cycle.position}", "tx")
    for line in (f"POSITION:{cycle.target}", "BUSY:0", "AUTO:0"):
        event(cycle, "egg", line)
    cycle.tick()


def record(vision, cycle, cls="FERTILE", inspection_id=None):
    inspection_id = cycle.inspection_id if inspection_id is None else inspection_id
    vision.latest = {"inspection_id": inspection_id, "timestamp": cycle.inspection_after,
                     "state": cls}
    vision.scan = {"scan_id": f"scan-{inspection_id}", "final_class": cls,
                   "inspection_id": inspection_id, "captured_at": cycle.inspection_after}


@pytest.mark.parametrize("mode,cls,command,angle", [
    ("Classify & sort", "FERTILE", "SORT:FERTILE", 30),
    ("Classify & sort", "INFERTILE", "SORT:INFERTILE", 90),
    ("Detect & block", "INFERTILE", "SERVO:30", 30),
])
def test_full_cycle_holds_servo_during_clearance_and_repeats(setup_cycle, mode, cls, command, angle):
    cycle, rig, vision, now = setup_cycle
    cycle.settings = replace(cycle.settings, mode=mode)
    initialize(cycle, position=1000)
    assert rig.links["egg"].commands[-1] == "JOG:120"
    assert cycle.target == 1120 and vision.suspended
    complete_move(cycle)
    assert cycle.state == "INSPECTING" and not vision.suspended
    record(vision, cycle, cls)
    cycle.tick()
    assert rig.links["egg"].commands[-1] == "JOG:40"
    assert vision.routed == [f"scan-{cycle.inspection_id}"] and vision.suspended
    complete_move(cycle)
    assert rig.links["servo"].commands[-1] == command
    assert cycle.state == "BLOCKING"
    # No clearance movement before the gate angle is reported.
    count = len(rig.links["egg"].commands)
    cycle.tick()
    assert len(rig.links["egg"].commands) == count
    event(cycle, "servo", command, "tx")
    event(cycle, "servo", f"ANGLE:{angle}")
    cycle.tick()
    assert cycle.state == "CLEARING" and rig.links["egg"].commands[-1] == "JOG:40"
    assert rig.links["servo"].commands[-1] == command
    complete_move(cycle)
    assert cycle.state == "RESETTING" and rig.links["servo"].commands[-1] == "SERVO:90"
    event(cycle, "servo", "SERVO:90", "tx")
    event(cycle, "servo", "ANGLE:90")
    cycle.tick()
    assert cycle.completed == 1 and cycle.state == "TO_CAMERA"
    assert cycle.target == 1320  # 1000 + 120 + 40 + 40 + next 120
    assert "START" not in rig.links["egg"].commands and rig.stops == 0


def test_old_feedback_and_elapsed_time_do_not_complete_a_move(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    initialize(cycle)
    # Unsolicited or buffered pre-command target telemetry cannot complete it.
    for line in ("POSITION:120", "BUSY:0", "AUTO:0"):
        event(cycle, "egg", line)
    cycle.tick()
    assert cycle.state == "TO_CAMERA"
    event(cycle, "egg", "JOG:120", "tx")
    event(cycle, "egg", "POSITION:120")
    event(cycle, "egg", "BUSY:1")
    event(cycle, "egg", "AUTO:0")
    now[0] += 0.5
    cycle.tick()
    assert cycle.state == "TO_CAMERA"
    event(cycle, "egg", "BUSY:0")
    cycle.tick()
    assert cycle.state == "INSPECTING"


def test_only_fresh_persisted_station_capture_resumes_stepper(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    initialize(cycle)
    complete_move(cycle)
    record(vision, cycle, inspection_id=cycle.inspection_id - 1)
    cycle.tick()
    assert cycle.state == "INSPECTING"
    record(vision, cycle)
    vision.scan = None
    cycle.tick()
    assert cycle.state == "INSPECTING"
    record(vision, cycle)
    vision.scan["captured_at"] -= 1
    cycle.tick()
    assert cycle.state == "INSPECTING"
    record(vision, cycle)
    cycle.tick()
    assert cycle.state == "TO_GATE"


@pytest.mark.parametrize("fault", ["no egg", "low confidence", "serial error", "disconnect", "camera lost", "missing feedback"])
def test_faults_hold_for_manual_review_and_stop_both_controllers(setup_cycle, fault):
    cycle, rig, vision, now = setup_cycle
    initialize(cycle)
    if fault != "missing feedback":
        complete_move(cycle)
    if fault == "no egg" or fault == "missing feedback":
        now[0] = cycle.deadline + 0.1
    elif fault == "low confidence":
        record(vision, cycle, "MANUAL_REVIEW")
    elif fault == "serial error":
        event(cycle, "egg", "ERROR:SYSTEM_BUSY")
    elif fault == "disconnect":
        rig.links["servo"].ready = False
    else:
        vision.active = False
    cycle.tick()
    assert cycle.state == "MANUAL_REVIEW" and not cycle.active
    assert rig.stops == 1 and rig.links["egg"].commands[-1] == "STOP"
    assert vision.suspended
    if fault != "disconnect":
        assert rig.links["servo"].commands[-1] == "RESET"


def test_stop_cancels_repeat_and_ignores_late_replies(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    initialize(cycle)
    cycle.stop()
    before = list(rig.links["egg"].commands)
    for line in ("POSITION:120", "BUSY:0", "AUTO:0"):
        event(cycle, "egg", line)
    cycle.tick()
    assert cycle.state == "STOPPED" and rig.links["egg"].commands == before
    assert rig.stops == 1


def test_busy_board_and_simulated_or_absent_hardware_cannot_run(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    event(cycle, "egg", "STATUS", "tx")
    event(cycle, "egg", "BUSY:1")
    cycle.tick()
    assert cycle.state == "MANUAL_REVIEW"
    for role in ("egg", "servo"):
        rig.links[role].simulated = True
        with pytest.raises(ValueError, match="real"):
            cycle.start(CycleSettings())
        rig.links[role].simulated = False
    vision.active = False
    with pytest.raises(ValueError, match="camera"):
        cycle.start(CycleSettings())


def test_servo_requires_echo_and_mechanical_settling_before_clearance(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    initialize(cycle)
    complete_move(cycle)
    record(vision, cycle)
    cycle.tick()
    complete_move(cycle)
    cycle.settings = replace(cycle.settings, servo_settle_ms=300)
    event(cycle, "servo", "SORT:FERTILE", "tx")
    event(cycle, "servo", "ANGLE:30")
    cycle.tick()
    assert cycle.state == "BLOCKING"
    now[0] += 0.31
    cycle.tick()
    assert cycle.state == "CLEARING"


def test_initial_move_waits_for_model_and_store_readiness(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    vision.ready = False
    initialize(cycle)
    assert cycle.state == "INITIALIZING"
    assert not any(command.startswith("JOG:") for command in rig.links["egg"].commands)
    vision.ready = True
    cycle.tick()
    assert cycle.state == "TO_CAMERA"


def test_maximum_servo_settling_does_not_exceed_phase_timeout(setup_cycle):
    cycle, rig, vision, now = setup_cycle
    initialize(cycle)
    complete_move(cycle)
    record(vision, cycle)
    cycle.tick()
    cycle.settings = replace(cycle.settings, servo_settle_ms=5000)
    complete_move(cycle)
    event(cycle, "servo", "SORT:FERTILE", "tx")
    event(cycle, "servo", "ANGLE:30")
    cycle.tick()
    now[0] += 5.01
    cycle.tick()
    assert cycle.state == "CLEARING" and rig.stops == 0


@pytest.mark.parametrize("settings", [
    CycleSettings(camera_steps=0), CycleSettings(step_delay=199), CycleSettings(neutral_angle=181),
    CycleSettings(detection_timeout=0), CycleSettings(mode="Unknown"),
    CycleSettings(mode="Detect & block", block_angle=90),
])
def test_invalid_settings_do_not_enqueue_any_command(settings):
    rig, vision = Rig(), Vision()
    with pytest.raises(ValueError):
        AutomaticCycle(rig, vision).start(settings)
    assert not any(link.commands for link in rig.links.values())
