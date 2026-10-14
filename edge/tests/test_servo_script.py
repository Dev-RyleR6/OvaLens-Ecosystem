"""COM7-only servo diagnostic with the real serial worker and simulated v3 bytes."""
from pathlib import Path
import importlib.util
import sys
import threading
import serial
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_three_board import Wire
from test_stepper_script import fixture_link

spec = importlib.util.spec_from_file_location("servo_diagnostic", Path(__file__).resolve().parents[2] / "scripts/test_servo.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class ServoWire(Wire):
    def __init__(self, *, role="EGG_CONTROLLER", paused=True, sensor=False, wrong_angle=False,
                 lose_pause=False, fault_on_move=False, busy=False, state="WAITING"):
        self.paused, self.sensor, self.busy, self.egg_state = paused, sensor, busy, state
        self.wrong_angle, self.lose_pause, self.fault_on_move = wrong_angle, lose_pause, fault_on_move
        super().__init__(role)

    def report(self, ident=None):
        return (super().report(ident).replace("PAUSED:1", f"PAUSED:{int(self.paused)}")
                .replace("SENSOR:0", f"SENSOR:{int(self.sensor)}")
                .replace("BUSY:0", f"BUSY:{int(self.busy)}")
                .replace("STATE:WAITING", "STATE:" + self.egg_state))

    def write(self, data):
        text = data.decode().strip()
        if text.startswith("@"):
            ident, command = text[1:].split(" ", 1)
            if command.startswith("SERVO:") or command == "PAUSE":
                self.writes.append(text)
                self.last_id = int(ident)
                if command == "PAUSE":
                    self.paused, reply = True, "OK:PAUSE"
                else:
                    self.angle = str(int(command.split(":", 1)[1]) + int(self.wrong_angle))
                    self.paused = not self.lose_pause
                    if self.fault_on_move:
                        self.fault = "SERVO_ATTACH"
                    reply = "OK:SERVO_DONE"
                self.emit(f"ID:{ident}:{reply}\n" + self.report(int(ident)))
                return len(data)
        return super().write(data)


def commands(wire):
    return [w.split(" ", 1)[1] for w in wire.writes if w.startswith("@")]


@pytest.mark.parametrize("angles", [[90, 120, 90], [120], [0, 180, 90]])
def test_servo_sequence_uses_only_com7_and_keeps_pause_held(angles):
    wire = ServoWire()
    factory, opened, links = fixture_link(wire)
    output = []
    args = diagnostic.arguments(["--hold-ms", "0", "--angles", *map(str, angles)])
    assert diagnostic.test_servo(args, factory=factory, prompt=lambda _: "y", output=output.append)
    assert opened == ["COM7"] and wire.closed and "ESTOP" in wire.writes
    assert not links[0]._thread.is_alive() and wire.paused
    sent = commands(wire)
    assert sent[:3] == ["STATUS", "ACK_FAULT", "PAUSE"]
    assert [s for s in sent if s.startswith("SERVO:")] == [f"SERVO:{a}" for a in angles]
    assert all(s == "STATUS" or s == "ACK_FAULT" or s == "PAUSE" or s.startswith("SERVO:") for s in sent)
    assert any("do not prove" in text for text in output)


@pytest.mark.parametrize("check", [False, True])
def test_declining_confirmation_never_opens_port_even_for_status(check):
    factory = Mock()
    assert not diagnostic.test_servo(diagnostic.arguments(["--check"] if check else []),
                                    factory=factory, prompt=lambda _: "n", output=lambda _: None)
    factory.assert_not_called()


def test_check_only_never_acknowledges_faults_or_requests_angle():
    wire = ServoWire(sensor=True)
    factory, opened, _ = fixture_link(wire)
    assert diagnostic.test_servo(diagnostic.arguments(["--check"]), factory=factory,
                                 prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM7"] and wire.closed and commands(wire) == ["STATUS"]


def test_startup_busy_is_allowed_to_settle_before_fault_acknowledgement():
    wire = ServoWire(busy=True)
    factory, _, _ = fixture_link(wire)
    def settled():
        wire.busy = False
        wire.emit(wire.report())
    timer = threading.Timer(.1, settled)
    timer.start()
    try:
        assert diagnostic.test_servo(diagnostic.arguments(["--angles", "90", "--hold-ms", "0"]),
                                     factory=factory, prompt=lambda _: "y", output=lambda _: None)
    finally:
        timer.join()
    assert "ACK_FAULT" in commands(wire) and wire.closed


def test_ir_changes_during_observation_do_not_interrupt_servo_test():
    wire = ServoWire()
    timers = []
    original = wire.write
    def write(data):
        result = original(data)
        if b" SERVO:" in data and not timers:
            def blocked():
                wire.sensor = True
                wire.egg_state = "HOLDING"
                wire.emit(wire.report())
            timer = threading.Timer(.06, blocked)
            timers.append(timer)
            timer.start()
        return result
    wire.write = write
    factory, opened, _ = fixture_link(wire)
    try:
        assert diagnostic.test_servo(diagnostic.arguments(["--hold-ms", "300"]), factory=factory,
                                     prompt=lambda _: "y", output=lambda _: None)
    finally:
        for timer in timers:
            timer.join()
    assert opened == ["COM7"] and wire.closed and "ESTOP" in wire.writes
    assert [c for c in commands(wire) if c.startswith("SERVO:")] == ["SERVO:90", "SERVO:120", "SERVO:90"]


@pytest.mark.parametrize("sensor,state", [(True, "HOLDING"), (False, "CLEARING"), (None, None)])
def test_servo_works_with_blocked_or_absent_ir_and_any_egg_cycle_state(sensor, state):
    wire = ServoWire(sensor=bool(sensor), state=state or "WAITING")
    if sensor is None:
        report = wire.report
        wire.report = lambda ident=None: "\n".join(line for line in report(ident).splitlines()
                                                   if "SENSOR:" not in line) + "\n"
        # Discard the simulated boot report so absence applies from identification onward.
        while not wire.inbox.empty():
            wire.inbox.get_nowait()
    factory, opened, _ = fixture_link(wire)
    assert diagnostic.test_servo(diagnostic.arguments(["--hold-ms", "0"]), factory=factory,
                                 prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM7"] and wire.closed
    assert [c for c in commands(wire) if c.startswith("SERVO:")] == ["SERVO:90", "SERVO:120", "SERVO:90"]


@pytest.mark.parametrize("failure", ["pause", "role", "fault", "wrong-angle", "lost-pause", "move-fault", "interrupt"])
def test_unsafe_or_failed_test_stops_without_retry_or_later_angles(failure):
    wire = ServoWire(paused=failure != "pause",
                     role="CONVEYOR" if failure == "role" else "EGG_CONTROLLER",
                     wrong_angle=failure == "wrong-angle", lose_pause=failure == "lost-pause",
                     fault_on_move=failure == "move-fault")
    if failure == "fault":
        wire.fault = "SERVO_ATTACH"
    factory, opened, links = fixture_link(wire)
    if failure == "interrupt":
        original = factory
        def factory(*args, **kwargs):
            link = original(*args, **kwargs)
            command = link.command
            def interrupted(text, *args, **kwargs):
                if text.startswith("SERVO:"):
                    raise KeyboardInterrupt()
                return command(text, *args, **kwargs)
            link.command = interrupted
            return link
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else RuntimeError):
        diagnostic.test_servo(diagnostic.arguments(["--hold-ms", "0"]), factory=factory,
                              prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM7"] and wire.closed and "ESTOP" in wire.writes
    assert sum(c.startswith("SERVO:") for c in commands(wire)) <= 1
    assert not links[0]._thread.is_alive()


@pytest.mark.parametrize("args", [["--angles", "-1"], ["--angles", "181"],
    ["--angles", *("90" for _ in range(11))], ["--hold-ms", "-1"], ["--hold-ms", "5001"]])
def test_invalid_angles_and_observation_time_rejected_before_connection(args):
    with pytest.raises(SystemExit):
        diagnostic.arguments(args)


class StartupPort:
    """Clocked transport for boot synchronization, without opening a real port."""
    def __init__(self, clock, failure=None):
        self.clock, self.failure = clock, failure
        self.closed, self.writes, self.reset_at = False, [], None
        self.reads = 0

    def reset_input_buffer(self):
        self.reset_at = self.clock[0]
        if self.failure == "interrupt":
            raise KeyboardInterrupt()

    def write(self, data):
        self.writes.append((self.clock[0], data))
        return 0 if self.failure == "short-write" else len(data)

    def read(self, count):
        self.clock[0] += .02
        self.reads += 1
        return b"ERROR:INVALID_LINE\n" if self.reads == 1 or self.failure == "noise" else b""

    def close(self):
        self.closed = True


@pytest.mark.parametrize("failure", [None, "interrupt", "short-write", "noise"])
def test_serial_startup_waits_drains_partial_line_and_closes_on_failure(monkeypatch, failure):
    clock = [0.0]
    port = StartupPort(clock, failure)
    opening = Mock(return_value=port)
    monkeypatch.setattr(serial, "Serial", opening)
    monkeypatch.setattr(diagnostic.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(diagnostic.time, "monotonic", lambda: clock[0])
    if failure:
        with pytest.raises(KeyboardInterrupt if failure == "interrupt" else RuntimeError):
            diagnostic.open_servo_port("COM7", 115200, timeout=.02, write_timeout=.2)
        assert port.closed
    else:
        assert diagnostic.open_servo_port("COM7", 115200, timeout=.02, write_timeout=.2) is port
        assert not port.closed and port.reads > 1 and clock[0] >= 2.2
    opening.assert_called_once_with("COM7", 115200, timeout=.02, write_timeout=.2)
    assert port.reset_at == 2
    assert port.writes == ([] if failure == "interrupt" else [(2, b"\n")])


def test_default_servo_path_recovers_only_pre_handshake_partial_line(monkeypatch):
    wire = ServoWire()
    original = wire.write
    def reset_input():
        while not wire.inbox.empty():
            wire.inbox.get_nowait()
    def write(data):
        if data == b"\n":
            wire.writes.append("STARTUP_DELIMITER")
            wire.emit("ERROR:INVALID_LINE\n")
            return 1
        return original(data)
    wire.reset_input_buffer, wire.write = reset_input, write
    opening = Mock(return_value=wire)
    monkeypatch.setattr(serial, "Serial", opening)
    assert diagnostic.test_servo(diagnostic.arguments(["--hold-ms", "0"]),
                                 prompt=lambda _: "y", output=lambda _: None)
    opening.assert_called_once_with("COM7", 115200, timeout=.02, write_timeout=.2)
    assert wire.writes[0] == "STARTUP_DELIMITER" and wire.closed
    assert [c for c in commands(wire) if c.startswith("SERVO:")] == ["SERVO:90", "SERVO:120", "SERVO:90"]


def test_stop_during_boot_closes_port_without_startup_or_motion_commands(monkeypatch):
    event = threading.Event()
    event.set()
    port = StartupPort([0.0])
    monkeypatch.setattr(serial, "Serial", Mock(return_value=port))
    with pytest.raises(RuntimeError, match="stopped during serial startup"):
        diagnostic.open_servo_port("COM7", 115200, timeout=.02, stop_event=event)
    assert port.closed and port.writes == [] and port.reset_at is None


@pytest.mark.parametrize("when", ["handshake", "move"])
def test_invalid_line_after_startup_is_fatal_without_motion_retry(when):
    wire = ServoWire()
    original = wire.write
    def write(data):
        if (when == "handshake" and data == b"HELLO\n") or (when == "move" and b" SERVO:" in data):
            wire.writes.append(data.decode().strip())
            wire.emit("ERROR:INVALID_LINE\n")
            return len(data)
        return original(data)
    wire.write = write
    factory, opened, _ = fixture_link(wire)
    with pytest.raises(RuntimeError, match="ERROR:INVALID_LINE"):
        diagnostic.test_servo(diagnostic.arguments(["--hold-ms", "0"]), factory=factory,
                              prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM7"] and wire.closed and "ESTOP" in wire.writes
    assert sum(c.startswith("SERVO:") for c in commands(wire)) == int(when == "move")
