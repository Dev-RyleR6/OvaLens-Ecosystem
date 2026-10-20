"""COM5-only diagnostic against the real serial worker and simulated v3 bytes."""
from pathlib import Path
import importlib.util
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.iot.dual_board import BoardLink
from test_three_board import Wire

spec = importlib.util.spec_from_file_location("stepper_diagnostic", Path(__file__).resolve().parents[2] / "scripts/test_stepper.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class StepperWire(Wire):
    def __init__(self, *, paused=False, early=False, wrong_speed=False, role="CONVEYOR"):
        self.position, self.paused, self.speed = 0, paused, 3000
        self.early, self.wrong_speed = early, wrong_speed
        super().__init__(role)

    def report(self, ident=None):
        prefix = f"ID:{ident}:" if ident is not None else ""
        return (super().report(ident).replace("POSITION:0", f"POSITION:{self.position}")
                .replace("PAUSED:1", f"PAUSED:{int(self.paused)}")
                .replace(prefix + "STATE:", prefix + f"SPEED:{self.speed}\n" + prefix + "STATE:"))

    def write(self, data):
        text = data.decode().strip()
        if text.startswith("@"):
            ident, command = text[1:].split(" ", 1)
            if command.startswith(("JOG:", "SPEED:")):
                self.writes.append(text)
                self.last_id = int(ident)
                if command.startswith("JOG:"):
                    self.position += int(command.split(":", 1)[1]) - int(self.early)
                    reply = "OK:EGG_STOPPED" if self.early else "OK:MOVE_DONE"
                else:
                    self.speed = int(command.split(":", 1)[1]) - int(self.wrong_speed)
                    reply = "OK:SPEED"
                self.emit(f"ID:{ident}:{reply}\n" + self.report(int(ident)))
                return len(data)
        return super().write(data)


def fixture_link(wire):
    opened, links = [], []
    def factory(role, port, **kwargs):
        def serial_factory(selected, *args, **options):
            opened.append(selected)
            return wire
        link = BoardLink(role, port, serial_factory=serial_factory, **kwargs)
        links.append(link)
        return link
    return factory, opened, links


@pytest.mark.parametrize("steps", [50, -50, 1000])
def test_finite_jog_opens_only_com5_and_stops_without_homing(steps):
    wire = StepperWire()
    factory, opened, links = fixture_link(wire)
    messages = []
    assert diagnostic.test_stepper(diagnostic.arguments(["--steps", str(steps)]),
                                   factory=factory, prompt=lambda _: "y", output=messages.append)
    assert opened == ["COM5"] and wire.closed and "ESTOP" in wire.writes
    assert not links[0]._thread.is_alive()
    commands = [w.split(" ", 1)[1] for w in wire.writes if w.startswith("@")]
    assert commands == ["STATUS", "ACK_FAULT", "SPEED:5000", "STATUS", f"JOG:{steps}"]
    assert wire.position == steps and any("physically moved" in m for m in messages)


def test_cancel_does_not_open_any_port():
    factory = Mock()
    assert not diagnostic.test_stepper(diagnostic.arguments([]), factory=factory,
                                       prompt=lambda _: "n", output=lambda _: None)
    factory.assert_not_called()


def test_paused_hardware_never_acknowledges_faults_or_dispatches_motion():
    wire = StepperWire(paused=True)
    factory, opened, _ = fixture_link(wire)
    with pytest.raises(RuntimeError, match="Hardware pause is active"):
        diagnostic.test_stepper(diagnostic.arguments([]), factory=factory,
                                prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM5"] and wire.closed and "ESTOP" in wire.writes
    assert [w.split(" ", 1)[1] for w in wire.writes if w.startswith("@")] == ["STATUS"]


def test_check_only_reports_paused_status_without_ack_or_jog():
    wire = StepperWire(paused=True)
    factory, opened, _ = fixture_link(wire)
    prompt = Mock(side_effect=AssertionError("No motion prompt for --check"))
    assert diagnostic.test_stepper(diagnostic.arguments(["--check"]), factory=factory,
                                   prompt=prompt, output=lambda _: None)
    prompt.assert_not_called()
    assert opened == ["COM5"] and wire.closed
    assert [w.split(" ", 1)[1] for w in wire.writes if w.startswith("@")] == ["STATUS"]


@pytest.mark.parametrize("failure", ["early-stop", "speed", "role", "fault", "interrupt"])
def test_failed_test_stops_closes_and_never_retries(failure):
    wire = StepperWire(early=failure == "early-stop", wrong_speed=failure == "speed",
                       role="LIGHT_CONTROLLER" if failure == "role" else "CONVEYOR")
    if failure == "fault":
        wire.fault = "TIMER_INIT"
    factory, opened, links = fixture_link(wire)
    if failure == "interrupt":
        original_factory = factory
        def factory(*args, **kwargs):
            link = original_factory(*args, **kwargs)
            command = link.command
            def interrupted(text, *args, **kwargs):
                if text.startswith("JOG:"):
                    raise KeyboardInterrupt()
                return command(text, *args, **kwargs)
            link.command = interrupted
            return link
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else RuntimeError):
        diagnostic.test_stepper(diagnostic.arguments([]), factory=factory,
                                prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM5"] and wire.closed and "ESTOP" in wire.writes
    assert sum(" JOG:" in w for w in wire.writes) <= 1
    assert not links[0]._thread.is_alive()


@pytest.mark.parametrize("args", [["--steps", "0"], ["--steps", "1001"], ["--steps", "-1001"],
    ["--speed-us", "199"], ["--speed-us", "5001"], ["--port", " "]])
def test_invalid_arguments_rejected_before_hardware(args):
    with pytest.raises(SystemExit):
        diagnostic.arguments(args)
