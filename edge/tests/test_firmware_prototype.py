"""Hardware-free contract and worker tests for TASK-NEW-FW-APP-01."""

from pathlib import Path
import queue
import sys
import threading
import time

import pytest
import serial

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from firmware.prototype.controller import (  # noqa: E402
    PrototypeRig, SerialLink, SimulatedBoard, choose_port, egg_status, integer, validate_command,
)


def wait_for(predicate):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    pytest.fail("Worker did not reach the expected state")


def collect(events):
    result = []
    while not events.empty():
        result.append(events.get_nowait())
    return result


@pytest.mark.parametrize("role,command", [
    ("egg", "SORT:FERTILE"), ("servo", "START"), ("servo", "SORT:DEAD"),
    ("servo", "SERVO:181"), ("egg", "SPEED:199"), ("egg", "TEST:0"),
    ("servo", "SERVO:90\nRESET"), ("egg", "JOG:1.5"), ("egg", "TEST:100001"),
])
def test_rejects_wrong_board_and_invalid_motion(role, command):
    with pytest.raises(ValueError):
        validate_command(role, command)


@pytest.mark.parametrize("role,command", [
    ("egg", "START"), ("egg", "STOP"), ("egg", "HOME"), ("egg", "STATUS"),
    ("egg", "SETHOME"), ("egg", "SETCHAMBER"), ("egg", "SETOUTPUT"),
    ("egg", "GOTO:CHAMBER"), ("egg", "GOTO:OUTPUT"), ("egg", "JOG:-100"),
    ("egg", "SPEED:800"), ("egg", "TEST:500"), ("servo", "STATUS"),
    ("servo", "RESET"), ("servo", "SERVO:90"), ("servo", "SET_FERTILE:30"),
    ("servo", "SET_INFERTILE:90"), ("servo", "SORT:FERTILE"), ("servo", "SORT:INFERTILE"),
])
def test_legacy_command_contract(role, command):
    assert validate_command(role, command) == command


def test_operator_validation_does_not_clamp_or_truncate():
    assert integer(" 180 ", 0, 180, "Angle") == 180
    for value in ("abc", "1.5", 90.5, -1, 181):
        with pytest.raises(ValueError):
            integer(value, 0, 180, "Angle")


def test_hardware_port_choices_survive_refresh_and_do_not_pick_one_board_twice():
    ports = ["COM7", "COM5"]
    assert choose_port(ports, preferred="COM5") == "COM5"
    assert choose_port(ports, preferred="COM7", used={"COM5"}) == "COM7"
    assert choose_port(ports, current="COM5", preferred="COM7") == "COM5"
    assert choose_port(["COM7"], current="COM5") == "COM5"
    assert choose_port(ports, used={"COM7"}) == "COM5"
    assert choose_port(["COM5"], used={"COM5"}) == "No ports"


@pytest.mark.parametrize("busy,automatic,state", [
    ("0", "0", "IDLE"), ("1", "0", "MOVING"), ("0", "1", "AUTO_RUNNING"),
    ("1", "1", "AUTO_RUNNING"), (None, None, "RESPONDING"),
])
def test_deployed_conveyor_status_flags(busy, automatic, state):
    assert egg_status(busy, automatic) == state


def test_simulated_calibration_motion_and_two_class_presets():
    egg = SimulatedBoard("egg")
    egg.execute("JOG:150")
    assert "CHAMBER:150" in egg.execute("SETCHAMBER")
    egg.execute("JOG:100")
    egg.execute("SETOUTPUT")
    egg.execute("HOME")
    assert "POSITION:150" in egg.execute("GOTO:CHAMBER")
    assert "POSITION:250" in egg.execute("GOTO:OUTPUT")
    assert egg.execute("TEST:500") == ["ERROR:TEST_REQUIRES_HOME"]
    egg.execute("HOME")
    assert "STATE:TEST_COMPLETE" in egg.execute("TEST:500")
    egg.execute("START")
    assert egg.execute("JOG:1") == ["ERROR:SYSTEM_BUSY"]
    assert "STATE:STOPPED" in egg.execute("STOP")
    assert not egg.running and egg.position == 0
    servo = SimulatedBoard("servo")
    servo.execute("SET_FERTILE:45")
    servo.execute("SET_INFERTILE:120")
    assert "ANGLE:45" in servo.execute("SORT:FERTILE")
    assert "ANGLE:120" in servo.execute("SORT:INFERTILE")
    assert "ANGLE:90" in servo.execute("RESET")


class FakeSerial:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.writes = []
        self.threads = []
        self.closed = False
        self.input = bytearray(b"POSITION:12\nSTATE:HOME\nANGLE:90")

    @property
    def in_waiting(self):
        return len(self.input)

    def read(self, count):
        self.threads.append(threading.current_thread().name)
        if not self.input:
            time.sleep(0.005)
        value = bytes(self.input[:count])
        del self.input[:count]
        return value

    def write(self, data):
        self.threads.append(threading.current_thread().name)
        self.writes.append(data)
        return len(data)

    def close(self):
        self.closed = True


def test_serial_io_is_on_worker_and_partial_lines_are_buffered():
    events, connections = queue.Queue(), []

    def factory(**kwargs):
        connection = FakeSerial(**kwargs)
        connections.append(connection)
        return connection

    link = SerialLink("egg", events, serial_factory=factory, boot_seconds=0)
    try:
        link.connect("COM5")
        wait_for(lambda: link.ready and len(connections[0].writes) >= 1)
        link.send_many(["SPEED:800", "TEST:500"])
        wait_for(lambda: b"TEST:500\n" in connections[0].writes)
        received = [event.value for event in collect(events) if event.kind == "rx"]
        assert received == ["POSITION:12", "STATE:HOME"]
        connections[0].input.extend(b"\n")
        wait_for(lambda: any(event.value == "ANGLE:90" for event in list(events.queue)))
        assert connections[0].writes[:3] == [b"STATUS\n", b"SPEED:800\n", b"TEST:500\n"]
        assert set(connections[0].threads) == {"OvaLens-Prototype-egg"}
        assert connections[0].kwargs["baudrate"] == 115200
    finally:
        link.disconnect()
        wait_for(lambda: not link.active)
    assert connections[0].closed
    assert connections[0].writes[-1] == b"STOP\n"


def test_batch_validation_is_atomic_and_stop_cancels_pending_motion():
    link = SerialLink("egg", queue.Queue())
    link.ready = True
    with pytest.raises(ValueError):
        link.send_many(["SPEED:800", "TEST:-1"])
    assert link._commands.empty()
    link.send_many(["SPEED:800", "TEST:500"])
    old_epoch = link._epoch
    link.send("STOP", priority=True)
    assert link._epoch != old_epoch
    assert link._commands.get_nowait() == (link._epoch, ("STOP",))
    assert link._commands.empty()


def test_failed_real_connection_stays_disconnected_without_mock_fallback():
    events = queue.Queue()

    def fail(**kwargs):
        raise serial.SerialException("Port unavailable")

    link = SerialLink("egg", events, serial_factory=fail)
    link.connect("COM9")
    wait_for(lambda: not link.active)
    assert not link.ready and not link.simulated
    assert any(event.kind == "error" and "Port unavailable" in event.value
               for event in collect(events))


def test_stop_interrupts_motion_batch_after_an_in_flight_write():
    started, release = threading.Event(), threading.Event()

    class SlowSerial(FakeSerial):
        def write(self, data):
            if data == b"SPEED:800\n":
                started.set()
                assert release.wait(2)
            return super().write(data)

    connection = SlowSerial()
    link = SerialLink("egg", queue.Queue(), serial_factory=lambda **kwargs: connection,
                      boot_seconds=0)
    try:
        link.connect("COM5")
        wait_for(lambda: link.ready)
        link.send_many(["SPEED:800", "TEST:500"])
        assert started.wait(2)
        # The GUI can enqueue STOP even while a USB write is still pending.
        link.send("STOP", priority=True)
        release.set()
        wait_for(lambda: b"STOP\n" in connection.writes)
        assert b"TEST:500\n" not in connection.writes
    finally:
        release.set()
        link.disconnect()
        wait_for(lambda: not link.active)


def test_duplicate_ports_are_rejected_and_disconnect_during_boot_cancels_start():
    connections = []

    def factory(**kwargs):
        connection = FakeSerial(**kwargs)
        connections.append(connection)
        return connection

    rig = PrototypeRig(queue.Queue(), serial_factory=factory, boot_seconds=5)
    try:
        rig.connect("egg", "COM5")
        wait_for(lambda: bool(connections))
        with pytest.raises(ValueError, match="different COM"):
            rig.connect("servo", "com5")
        with pytest.raises(ValueError):
            rig.start()
    finally:
        rig.close()
        wait_for(lambda: not rig.links["egg"].active)
    assert connections[0].closed and not connections[0].writes


def test_dual_simulation_routes_sort_and_joint_stop():
    events = queue.Queue()
    rig = PrototypeRig(events)
    try:
        rig.connect("egg", "", simulated=True)
        rig.connect("servo", "", simulated=True)
        wait_for(lambda: all(link.ready for link in rig.links.values()))
        rig.start()
        rig.links["servo"].send("SORT:FERTILE")
        wait_for(lambda: any(event.role == "servo" and event.value == "STATE:FERTILE"
                            for event in list(events.queue)))
        collect(events)
        rig.stop()
        wait_for(lambda: any(event.value == "STATE:STOPPED" for event in list(events.queue)))
        wait_for(lambda: any(event.value == "STATE:NEUTRAL" for event in list(events.queue)))
        rig.links["egg"].disconnect()
        wait_for(lambda: not rig.links["egg"].active)
        collect(events)
        with pytest.raises(ValueError):
            rig.stop()
        wait_for(lambda: any(event.role == "servo" and event.kind == "tx" and event.value == "RESET"
                            for event in list(events.queue)))
    finally:
        rig.close()
        wait_for(lambda: not any(link.active for link in rig.links.values()))


def test_mixed_simulated_and_physical_boards_cannot_start():
    rig = PrototypeRig(queue.Queue())
    for link in rig.links.values():
        link.ready = True
    rig.links["egg"].simulated = True
    with pytest.raises(ValueError, match="both boards"):
        rig.start()
    assert rig.links["egg"]._commands.empty()
