"""TASK-NEW-FW-SAFE-01: execute actual C++ sketches with host Arduino shims.

Requires g++/clang++ (CI or WSL). Tests are not physical stopping/ISR proofs.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

NATIVE = Path(__file__).parent / "firmware_native"


@pytest.fixture(scope="session")
def sketches(tmp_path_factory):
    compiler = shutil.which("g++") or shutil.which("clang++")
    if compiler is None:
        pytest.skip("Native firmware behavior tests require g++ or clang++")
    result = {}
    build = tmp_path_factory.mktemp("firmware-native")
    for board in ("conveyor", "servo"):
        executable = build / board
        command = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                   f"-I{NATIVE}", str(NATIVE / "driver.cpp"), "-o", str(executable)]
        if board == "conveyor":
            command.append("-DBOARD_CONVEYOR")
        subprocess.run(command, check=True, capture_output=True, text=True)
        result[board] = executable
    return result


def run(sketches, board, actions, *, fail_init=False):
    command = [str(sketches[board])]
    if fail_init:
        command.append("fail-init")
    return subprocess.run(command, input="\n".join(actions) + "\n", check=True,
                          capture_output=True, text=True).stdout.splitlines()


def ready(board):
    return ["SEND HELLO", "CLOCK 500", "SEND @1 ACK_FAULT"]


def test_finite_move_matches_id_and_rejects_duplicate(sketches):
    lines = run(sketches, "conveyor", ready("conveyor") + [
        "SEND @2 SETHOME", "SEND @3 JOG:2", "SEND @3 JOG:2",
        "TICKS 4", "SEND STATUS"])
    assert "ID:3:OK:MOVE_ACCEPTED" in lines
    assert "ID:3:ERROR:ID_REUSED" in lines
    assert lines.count("ID:3:OK:MOVE_DONE") == 1
    assert lines[-12] == "POSITION:2"


@pytest.mark.parametrize("stop", ["STOP", "HALT", "@1 STOP", "@1 HALT"])
def test_stop_cancels_without_return_home_even_with_old_id(sketches, stop):
    lines = run(sketches, "conveyor", ready("conveyor") + [
        "SEND @2 JOG:10", "TICKS 1", f"SEND {stop}", "TICKS 30", "SEND STATUS"])
    assert "ID:2:ERROR:MOVE_CANCELLED" in lines
    assert "ID:2:OK:MOVE_DONE" not in lines
    assert lines[-12] == "POSITION:1"
    assert lines[-1] == "STATE:HALTED"


@pytest.mark.parametrize("board", ["conveyor", "servo"])
def test_watchdog_latches_and_ping_does_not_clear_fault(sketches, board):
    motion = "JOG:10" if board == "conveyor" else "SERVO:120"
    lines = run(sketches, board, ready(board) + [
        "SEND @2 " + motion, "CLOCK 3000", "SEND HELLO", "SEND @3 " + motion,
        "SEND @4 ACK_FAULT", "SEND @5 " + motion])
    # Last heartbeat was at 0, so deadline is exactly 3000 ms.
    assert "ERROR:LINK_TIMEOUT" in lines
    assert "ID:3:ERROR:FAULT_LATCHED" in lines
    assert "ID:4:OK:FAULT_ACKNOWLEDGED" in lines
    assert "ID:5:OK:MOVE_ACCEPTED" in lines or "ID:5:OK:SERVO_ACCEPTED" in lines


@pytest.mark.parametrize("board", ["conveyor", "servo"])
def test_invalid_commands_do_not_keep_link_alive(sketches, board):
    lines = run(sketches, board, ready(board) + [
        "CLOCK 2000", "SEND @2 NONSENSE", "CLOCK 3000"])
    assert "ID:2:ERROR:INVALID_COMMAND" in lines
    assert "ERROR:LINK_TIMEOUT" in lines


def test_fault_invalidates_reference_and_calibrated_stations(sketches):
    lines = run(sketches, "conveyor", ready("conveyor") + [
        "SEND @2 SETHOME", "SEND @3 SETCHAMBER", "SEND @4 SETOUTPUT",
        "SEND ESTOP", "SEND @5 ACK_FAULT", "SEND @6 HOME", "SEND STATUS"])
    assert "ID:6:ERROR:REFERENCE_REQUIRED" in lines
    assert "REFERENCE_VALID:0" in lines[-12:]
    assert "STATIONS_VALID:0" in lines[-12:]


def test_servo_busy_rejection_and_correlated_timed_completion(sketches):
    lines = run(sketches, "servo", ready("servo") + [
        "SEND @2 SERVO:120", "SEND @3 SERVO:60", "CLOCK 1000", "SEND STATUS"])
    assert "ID:3:ERROR:SYSTEM_BUSY" in lines
    assert "ID:2:OK:SERVO_DONE" in lines
    assert "ANGLE:120" in lines[-10:]


def test_servo_estop_holds_angle_and_cancels_completion(sketches):
    lines = run(sketches, "servo", ready("servo") + [
        "SEND @2 SERVO:120", "SEND ESTOP", "CLOCK 1000", "SEND @3 RESET", "SEND STATUS"])
    assert "ID:2:ERROR:SERVO_CANCELLED" in lines
    assert "ID:2:OK:SERVO_DONE" not in lines
    assert "ID:3:ERROR:FAULT_LATCHED" in lines
    assert "ANGLE:120" in lines[-10:]


def test_custom_neutral_changes_reset_target_without_moving_on_configuration(sketches):
    lines = run(sketches, "servo", ready("servo") + [
        "SEND @2 SET_NEUTRAL:85", "SEND STATUS", "SEND @3 RESET", "CLOCK 1000"])
    assert "ID:2:ANGLE:90" in lines
    assert "ID:3:ANGLE:85" in lines
    assert "ID:3:OK:SERVO_DONE" in lines


@pytest.mark.parametrize("board,motion", [("conveyor", "JOG:1"), ("servo", "SERVO:100")])
def test_untagged_motion_and_startup_motion_are_rejected(sketches, board, motion):
    lines = run(sketches, board, ["SEND HELLO", "SEND " + motion, "SEND @1 " + motion])
    assert "ERROR:COMMAND_ID_REQUIRED" in lines
    assert "ID:1:ERROR:FAULT_LATCHED" in lines


@pytest.mark.parametrize("board", ["conveyor", "servo"])
def test_malformed_lines_and_overflow_do_not_execute_suffix(sketches, board):
    lines = run(sketches, board, ready(board) + [
        "SEND " + "x" * 100 + "HALT", "SEND @0 RESET", "SEND @-1 HALT",
        "SEND @2 " + ("JOG:1.5" if board == "conveyor" else "SERVO:181")])
    assert "ERROR:INVALID_LINE" in lines
    assert lines.count("ERROR:INVALID_ENVELOPE") == 2
    assert "ID:2:ERROR:INVALID_COMMAND" in lines


@pytest.mark.parametrize("board", ["conveyor", "servo"])
def test_watchdog_handles_millis_wrap(sketches, board):
    lines = run(sketches, board, [
        "CLOCK 4294966000", "SEND HELLO", "CLOCK 1704"])
    assert "ERROR:LINK_TIMEOUT" in lines


@pytest.mark.parametrize("board,error,motion", [
    ("conveyor", "ERROR:TIMER_INIT", "JOG:1"),
    ("servo", "ERROR:SERVO_ATTACH", "SERVO:100"),
])
def test_initialization_failure_never_accepts_movement(sketches, board, error, motion):
    lines = run(sketches, board, ["SEND HELLO", "SEND @1 ACK_FAULT", "SEND @2 " + motion],
                fail_init=True)
    assert error in lines
    assert not any("ACCEPTED" in line for line in lines)
