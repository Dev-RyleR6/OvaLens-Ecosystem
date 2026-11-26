"""TASK-NEW-EDGE-GATEFIRST-01: classify, save, position gate, then release."""
from concurrent.futures import Future
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_three_board import FakeLink, fixture, prediction, wait_for


@pytest.mark.parametrize("kind", ["FERTILE", "INFERTILE"])
def test_servo_command_precedes_display_hold_and_first_release(tmp_path, kind):
    cycle, db, rig = fixture(tmp_path, count=1)
    cycle._capture = lambda: (prediction(kind), {})
    cycle.settings.calibration.hold_ms = 50
    delay = cycle._delay
    def hold(seconds):
        assert cycle._gate_holder == 1
        assert rig.egg.values["ANGLE"] == str(cycle.settings.calibration.fertile_angle if kind == "FERTILE" else cycle.settings.calibration.infertile_angle)
        assert rig.conveyor.values["PAUSED"] == "1"
        assert not any(command == "RESUME" and position == 100 for _, command, position, _ in rig.trace)
        delay(seconds)
    cycle._delay = hold
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    gate = next(i for i, (_, text, _, _) in enumerate(rig.trace) if text.startswith("SORT:"))
    release = next(i for i, (_, text, position, _) in enumerate(rig.trace) if text == "RESUME" and position == 100)
    reset = next(i for i, (_, text, _, _) in enumerate(rig.trace) if text == "RESET")
    assert gate < release < reset
    assert rig.trace[gate][2:] == (100, 1)  # Still in chamber; local scan already committed.
    assert rig.trace[reset][2] == 517  # Gate retained until calibrated exit.


@pytest.mark.parametrize("cancel", [False, True])
def test_no_conveyor_release_while_servo_completion_is_pending(tmp_path, cancel):
    cycle, db, rig = fixture(tmp_path, count=1)
    command = rig.egg.command
    waiting, future = threading.Event(), Future()
    def slow_servo(text, timeout=3):
        reply = command(text, timeout)
        if text.startswith("SORT:"):
            rig.egg.values["BUSY"] = "1"
            waiting.set()
            return future
        return reply
    rig.egg.command = slow_servo
    thread = threading.Thread(target=cycle._run)
    thread.start()
    try:
        assert waiting.wait(2)
        assert db.get_unsynced_count() == 1
        assert rig.conveyor.values["PAUSED"] == "1"
        assert db.load_machine_state("station")["state"] == "SERVO_IN_FLIGHT"
        assert not any(text == "RESUME" and position == 100 for _, text, position, _ in rig.trace)
        if cancel:
            cycle.stop()
        else:
            rig.egg.values["BUSY"] = "0"
            future.set_result(dict(rig.egg.values))
        thread.join(2)
        assert not thread.is_alive()
        assert cycle.status["state"] == ("RECOVERY_REQUIRED" if cancel else "COMPLETE"), cycle.status
        if cancel:
            assert not any(text == "RESUME" and position == 100 for _, text, position, _ in rig.trace)
    finally:
        if thread.is_alive():
            cycle.stop()
            thread.join(2)


@pytest.mark.parametrize("failure", ["timeout", "wrong_angle", "busy", "lost_pause"])
def test_failed_gate_confirmation_holds_egg_and_preserves_durable_scan(tmp_path, failure):
    cycle, db, rig = fixture(tmp_path, count=1)
    command = rig.egg.command
    def failed_servo(text, timeout=3):
        reply = command(text, timeout)
        if text.startswith("SORT:"):
            future = Future()
            if failure == "timeout":
                future.set_exception(TimeoutError("Servo acknowledgement timeout"))
            else:
                values = reply.result()
                if failure == "wrong_angle":
                    values["ANGLE"] = "90"
                elif failure == "busy":
                    values["BUSY"] = "1"
                else:
                    rig.conveyor.values["PAUSED"] = "0"
                future.set_result(values)
            return future
        return reply
    rig.egg.command = failed_servo
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert db.get_unsynced_count() == 1
    assert db.load_machine_state("station")["holders"][0]["stage"] == "SAVED"
    assert not any(text == "RESUME" and position == 100 for _, text, position, _ in rig.trace)
    assert rig.trace[-1][1] == "ESTOP"


def test_gate_exit_at_exact_next_arrival_is_cleared_before_new_preset(tmp_path):
    cycle, db, rig = fixture(tmp_path, arrivals=[100, 517])
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    assert cycle.count == cycle.routed == 2
    gate_events = [(text, position) for _, text, position, _ in rig.trace if text.startswith("SORT:") or text == "RESET"]
    assert gate_events == [("SORT:FERTILE", 100), ("RESET", 517), ("SORT:INFERTILE", 517), ("RESET", 934)]


def unified_reject(tmp_path, arrivals=None, count=1):
    cycle, db, rig = fixture(tmp_path, count=count, arrivals=arrivals)
    cycle.settings.rig_profile = "unified_v4"
    cycle.settings.calibration.speed_us = 4000
    link = FakeLink("UNIFIED", rig)
    rig.conveyor = rig.egg = rig.servo = rig.light = link
    rig.links = (link,)
    cycle._capture = lambda: (prediction("INFERTILE"), {})
    return cycle, db, rig


@pytest.mark.parametrize("lead_ms,trigger,limit", [(225, 338, 367), (500, 304, 367), (600, 292, 367), (0, 367, 372), (-100, 379, 384)])
def test_unified_reject_uses_saved_speed_and_configured_lead(tmp_path, lead_ms, trigger, limit):
    cycle, db, rig = unified_reject(tmp_path)
    cycle.settings.calibration.hold_ms = 300
    cycle.settings.calibration.reject_lead_ms = lead_ms
    cycle._delay = lambda seconds: pytest.fail("A reject should leave without the display hold")
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    assert cycle.routed == 1
    commands = [(text, position) for _, text, position, _ in rig.trace]
    release, reset = commands.index(("RESUME", 100)), commands.index(("RESET", 517))
    assert [(text, position, saved) for _, text, position, saved in rig.trace[release + 1:reset]
            if text.startswith(("ADVANCE", "SORT", "PAUSE", "RESUME", "SPEED"))] == [
        (f"ADVANCE_REJECT:417:{trigger}:{limit}:450", 100, 1),
    ]
    assert cycle.settings.calibration.speed_us == 4000
    assert db.load_machine_state("station")["rig_profile"] == "unified_v4"


@pytest.mark.parametrize("fault", ["missing_sweep", "wrong_sweep_position", "wrong_angle", "overlapping_egg"])
def test_unified_reject_stops_on_unconfirmed_gate_sweep(tmp_path, fault):
    overlapping = fault == "overlapping_egg"
    cycle, db, rig = unified_reject(tmp_path, arrivals=[100, 467] if overlapping else None,
                                    count=2 if overlapping else 1)
    original = rig.egg.command

    def command(text, timeout=3):
        reply = original(text, timeout)
        if text.startswith("ADVANCE_REJECT:") and not overlapping:
            values = reply.result()
            if fault == "missing_sweep":
                del values["REJECT_AT"]
            elif fault == "wrong_sweep_position":
                values["REJECT_AT"] = "468"
            else:
                values["ANGLE"] = "100"
            changed = Future()
            changed.set_result(values)
            return changed
        return reply

    rig.egg.command = command
    cycle._run()
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert cycle.routed == 0 and db.get_unsynced_count() == 1
    commands = [(text, position) for _, text, position, _ in rig.trace]
    assert sum(text.startswith("ADVANCE_REJECT:") for text, _ in commands) == 1
    assert not any(text == "RESET" for text, _ in commands)
    assert commands[-1] == ("ESTOP", 467 if overlapping else 517)
