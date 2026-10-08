"""Execute the actual three-board sketches; physical ISR timing is a rig check."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

NATIVE = Path(__file__).parent / "firmware_native"


@pytest.fixture(scope="session")
def three_sketches(tmp_path_factory):
    compiler = shutil.which("g++") or shutil.which("clang++")
    zig = os.getenv("OVALENS_TEST_ZIG")
    if not compiler and not zig:
        pytest.skip("C++ firmware execution requires g++/clang++ or OVALENS_TEST_ZIG")
    prefix = [compiler] if compiler else [zig, "c++", "-nostdlib++"]
    build, result = tmp_path_factory.mktemp("three-firmware"), {}
    for role in ("CONVEYOR", "EGG", "LIGHT"):
        target = build / (role + (".exe" if os.name == "nt" else ""))
        command = prefix + ["-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{NATIVE}",
                            f"-DBOARD_{role}", str(NATIVE / "three_board_driver.cpp"), "-o", str(target)]
        compiled = subprocess.run(command, capture_output=True, text=True, timeout=180)
        assert compiled.returncode == 0, compiled.stderr
        result[role] = target
    return result


def run(three_sketches, role, *actions, fail=False):
    command = [str(three_sketches[role])] + (["fail-init"] if fail else [])
    return subprocess.run(command, input="\n".join(actions) + "\n", capture_output=True,
                          text=True, check=True, timeout=10).stdout


def ready(role):
    return ["SEND HELLO", "CLOCK 500", "SEND @1 ACK_FAULT"] + (["SEND @2 SETHOME", "PIN 27 0"] if role == "CONVEYOR" else [])


@pytest.mark.parametrize("role", ["CONVEYOR", "EGG", "LIGHT"])
def test_startup_is_faulted_and_role_is_versioned(three_sketches, role):
    output = run(three_sketches, role, "SEND PING", "SEND STATUS")
    name = {"EGG": "EGG_CONTROLLER", "LIGHT": "LIGHT_CONTROLLER"}.get(role, role)
    assert f"PONG:{name}" in output and f"READY:{name}_V3:PROTOCOL=3" in output
    assert "FAULT:STARTUP_ACK_REQUIRED" in output
    if role == "EGG":
        assert "PAUSED:1" in output
    if role == "LIGHT":
        assert "LIGHT:0" in output


def test_hardware_pause_stops_and_preserves_position(three_sketches):
    output = run(three_sketches, "CONVEYOR", *ready("CONVEYOR"),
                 "SEND @3 ADVANCE:100", "TICKS 10", "PIN 27 1", "TICKS 10", "SEND STATUS")
    assert "ID:3:OK:EGG_STOPPED" in output
    assert output.count("POSITION:5") >= 2 and "REFERENCE_VALID:1" in output
    assert "POSITION:100" not in output


def test_conveyor_watchdog_expires_even_while_paused(three_sketches):
    output = run(three_sketches, "CONVEYOR", *ready("CONVEYOR"),
                 "SEND @3 ADVANCE:100", "PIN 27 1", "TICKS 2", "CLOCK 3000", "SEND PING", "SEND @4 ADVANCE:10")
    assert "FAULT:LINK_TIMEOUT" in output and "ERROR:FAULT_LATCHED" in output
    assert "REFERENCE_VALID:0" in output


def test_sensor_confirmation_clearance_and_single_event(three_sketches):
    output = run(three_sketches, "EGG", *ready("EGG"), "SEND @2 ARM", "SEND @3 RESUME",
                 "PIN 26 0", "CLOCK 539", "SEND STATUS", "CLOCK 540", "CLOCK 600",
                 "SEND @4 RESUME", "PIN 26 1", "CLOCK 949", "CLOCK 950", "SEND STATUS")
    assert output.count("EVENT:EGG_DETECTED:1") == 1
    assert output.count("EVENT:EGG_CLEARED:1") == 1
    assert "PAUSED:1" in output and output.rstrip().endswith("STATE:WAITING")


def test_servo_completion_presets_and_strict_number_parsing(three_sketches):
    output = run(three_sketches, "EGG", *ready("EGG"), "SEND @2 SORT:FERTILE", "CLOCK 1000",
                 "SEND @3 SORT:INFERTILE", "CLOCK 1500", "SEND @4 SERVO:abc", "SEND @5 SERVO:181")
    assert "ID:2:OK:SERVO_DONE" in output and "ID:2:ANGLE:180" in output
    assert "ID:3:ANGLE:120" in output
    assert "ID:4:ERROR:INVALID_COMMAND" in output and "ID:5:ERROR:INVALID_COMMAND" in output


@pytest.mark.parametrize("role,command", [("CONVEYOR", "ADVANCE:10"), ("EGG", "RESUME"), ("LIGHT", "LIGHT_ON")])
def test_ids_and_overflow_never_replay_actuation(three_sketches, role, command):
    identity = 3 if role == "CONVEYOR" else 2
    output = run(three_sketches, role, *ready(role), f"SEND @{identity} STATUS", f"SEND @{identity} {command}",
                 "SEND " + "x" * 100 + command, "SEND " + command)
    assert "ERROR:ID_REUSED" in output and "ERROR:INVALID_LINE" in output
    assert "ERROR:COMMAND_ID_REQUIRED" in output


@pytest.mark.parametrize("role", ["CONVEYOR", "EGG", "LIGHT"])
def test_watchdog_and_stop_are_latched(three_sketches, role):
    output = run(three_sketches, role, *ready(role), "CLOCK 3000", "SEND PING", "SEND @5 STATUS", "SEND @1 ESTOP")
    assert "FAULT:LINK_TIMEOUT" in output
    assert "ID:5:FAULT:LINK_TIMEOUT" in output
    assert "FAULT:EMERGENCY_STOP" in output
    if role == "EGG":
        assert "PAUSED:1" in output
    if role == "LIGHT":
        assert "LIGHT:0" in output


def test_lamp_hard_timeout_survives_heartbeats_and_clock_wrap(three_sketches):
    actions = ready("LIGHT") + ["CLOCK 4294966000", "SEND PING", "SEND @2 ACK_FAULT", "SEND @3 LIGHT_ON"]
    # Heartbeats keep the link alive, but do not renew the lamp's 15-second lease.
    for elapsed in range(2000, 16001, 2000):
        actions.extend([f"CLOCK {(4294966000 + elapsed) % 2**32}", "SEND PING"])
    output = run(three_sketches, "LIGHT", *actions)
    assert "WARN:AUTO_OFF_TIMEOUT" in output and "FAULT:LIGHT_AUTO_OFF_TIMEOUT" in output
    assert "LIGHT:0" in output


def test_reset_delay_counts_only_unpaused_time_and_new_sort_cancels_it(three_sketches):
    output = run(three_sketches, "EGG", *ready("EGG"), "SEND @2 SORT:FERTILE", "CLOCK 1000",
                 "SEND @3 GATE_RESET_DELAY:100", "CLOCK 1100", "SEND STATUS", "SEND @4 RESUME",
                 "CLOCK 1150", "SEND @5 SORT:INFERTILE", "CLOCK 1650", "SEND STATUS")
    assert "EVENT:GATE_RESET_DONE" not in output
    assert output.rstrip().endswith("STATE:WAITING") and "ID:5:ANGLE:120" in output


def test_scheduled_reset_emits_done_only_after_settling(three_sketches):
    output = run(three_sketches, "EGG", *ready("EGG"), "SEND @2 SORT:FERTILE", "CLOCK 1000",
                 "SEND @3 GATE_RESET_DELAY:100", "SEND @4 RESUME", "CLOCK 1100", "SEND STATUS", "CLOCK 1600")
    assert output.count("EVENT:GATE_RESET_DONE:0") == 1
    assert output.rfind("OK:SERVO_DONE") < output.rfind("EVENT:GATE_RESET_DONE")


def test_premature_new_egg_faults_and_holds_during_lockout(three_sketches):
    output = run(three_sketches, "EGG", *ready("EGG"), "SEND @2 ARM", "SEND @3 RESUME",
                 "PIN 26 0", "CLOCK 540", "SEND @4 RESUME", "PIN 26 1", "CLOCK 890", "PIN 26 0")
    assert "FAULT:FEED_LOCKOUT" in output and output.count("EVENT:EGG_DETECTED") == 1
    assert "PAUSED:1" in output


@pytest.mark.parametrize("role,command,error", [("CONVEYOR", "ADVANCE:1", "TIMER_INIT"), ("EGG", "SERVO:90", "SERVO_ATTACH")])
def test_initialization_failure_rejects_actuation(three_sketches, role, command, error):
    output = run(three_sketches, role, "SEND HELLO", "SEND @1 ACK_FAULT", f"SEND @2 {command}", fail=True)
    assert "ERROR:" + error in output and "OK:MOVE_ACCEPTED" not in output and "OK:SERVO_ACCEPTED" not in output
