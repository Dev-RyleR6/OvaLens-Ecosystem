"""COM9-only light diagnostic against the real worker and simulated v3 bytes."""
from pathlib import Path
import importlib.util
import sys
from unittest.mock import Mock

import pytest
import serial

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_three_board import Wire, wait_for
from test_stepper_script import fixture_link

spec = importlib.util.spec_from_file_location("light_diagnostic", Path(__file__).resolve().parents[2] / "scripts/test_light.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class LightWire(Wire):
    def report(self, ident=None):
        # Lamp firmware has no IR, servo or conveyor telemetry.
        prefix = f"ID:{ident}:" if ident is not None else ""
        fields = [f"LIGHT:{self.light}", "BUSY:0", f"FAULT:{self.fault}",
                  f"LAST_ID:{self.last_id}", "STATE:FAULT" if self.fault != "NONE" else "STATE:ON" if self.light == "1" else "STATE:OFF"]
        return "".join(prefix + field + "\n" for field in fields)

    def write(self, data):
        if data == b"ESTOP\n":
            self.light = "0"
        return super().write(data)

    def reset_input_buffer(self):
        while not self.inbox.empty():
            self.inbox.get_nowait()


def commands(wire):
    return [line.split(" ", 1)[1] for line in wire.writes if line.startswith("@")]


@pytest.mark.parametrize("cycles,seconds", [(2, 2), (1, 1), (5, 10)])
def test_bounded_light_sequence_opens_only_com9_and_finishes_off(monkeypatch, cycles, seconds):
    wire = LightWire("LIGHT_CONTROLLER")
    factory, opened, links = fixture_link(wire)
    holds = Mock()
    monkeypatch.setattr(diagnostic, "observe", holds)
    output = []
    assert diagnostic.test_light(diagnostic.arguments(["--cycles", str(cycles), "--seconds", str(seconds)]),
                                 factory=factory, prompt=lambda _: "y", output=output.append)
    assert opened == ["COM9"] and wire.closed and wire.light == "0"
    assert not links[0]._thread.is_alive() and "ESTOP" in wire.writes
    assert commands(wire) == ["STATUS", "ACK_FAULT"] + ["LIGHT_ON", "LIGHT_OFF"] * cycles
    assert [call.args[1:] for call in holds.call_args_list] == [(seconds, True), (1, False)] * (cycles - 1) + [(seconds, True)]
    assert any("Observe the actual lamp" in message for message in output)


def test_cancel_never_opens_any_port():
    factory = Mock()
    assert not diagnostic.test_light(diagnostic.arguments([]), factory=factory, prompt=lambda _: "n", output=lambda _: None)
    factory.assert_not_called()


@pytest.mark.parametrize("fault", ["NONE", "EMERGENCY_STOP", "LINK_TIMEOUT", "LIGHT_AUTO_OFF_TIMEOUT"])
def test_known_off_faults_can_be_acknowledged_before_testing(monkeypatch, fault):
    wire = LightWire("LIGHT_CONTROLLER")
    wire.fault = fault
    wire.reset_input_buffer()
    monkeypatch.setattr(diagnostic, "observe", Mock())
    factory, opened, _ = fixture_link(wire)
    assert diagnostic.test_light(diagnostic.arguments(["--cycles", "1"]), factory=factory,
                                 prompt=lambda _: "y", output=lambda _: None)
    assert ("ACK_FAULT" in commands(wire)) == (fault != "NONE")
    assert opened == ["COM9"] and wire.closed and wire.light == "0"


@pytest.mark.parametrize("failure", ["role", "version", "already-on", "unknown-fault", "bad-on", "bad-off", "error", "lost-reply", "interrupt", "disconnect"])
def test_errors_and_interrupts_request_off_and_never_retry_on(monkeypatch, failure):
    wire = LightWire("EGG_CONTROLLER" if failure == "role" else "LIGHT_CONTROLLER",
                     version=2 if failure == "version" else 3)
    if failure == "already-on":
        wire.light = "1"
    if failure == "unknown-fault":
        wire.fault = "RELAY_FAULT"
    original = wire.write
    def write(data):
        if b" LIGHT_ON" in data and failure in {"error", "lost-reply", "disconnect"}:
            wire.writes.append(data.decode().strip())
            wire.light = "1"
            if failure == "error":
                wire.emit("ERROR:INVALID_LINE\n")
            if failure == "disconnect":
                raise OSError("USB disconnected")
            return len(data)
        result = original(data)
        if (b" LIGHT_ON" in data and failure == "bad-on") or (b" LIGHT_OFF" in data and failure == "bad-off"):
            wire.reset_input_buffer()
            ident = int(data.decode().split(" ")[0][1:])
            wire.light = str(int(failure == "bad-off"))
            wire.emit(f"ID:{ident}:OK:LIGHT_{'OFF' if failure == 'bad-off' else 'ON'}\n" + wire.report(ident))
        return result
    wire.write = write
    def observe(*args):
        if failure == "interrupt":
            raise KeyboardInterrupt()
    monkeypatch.setattr(diagnostic, "observe", observe)
    factory, opened, links = fixture_link(wire)
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else RuntimeError):
        diagnostic.test_light(diagnostic.arguments([]), factory=factory, prompt=lambda _: "y", output=lambda _: None)
    assert opened == ["COM9"] and wire.closed and wire.light == "0" and "ESTOP" in wire.writes
    assert commands(wire).count("LIGHT_ON") <= 1 and not links[0]._thread.is_alive()


def test_hold_keeps_heartbeats_running_and_faults_stop_observation():
    wire = LightWire("LIGHT_CONTROLLER")
    factory, _, _ = fixture_link(wire)
    link = factory("LIGHT_CONTROLLER", "COM9", protocol=3)
    try:
        link.start()
        wait_for(lambda: link._status_complete)
        link.command("ACK_FAULT").result(1)
        link.command("LIGHT_ON").result(1)
        diagnostic.observe(link, .6, True)
        assert "STATUS" in wire.writes
        wire.emit("LIGHT:0\nBUSY:0\nFAULT:LIGHT_AUTO_OFF_TIMEOUT\nLAST_ID:2\nSTATE:FAULT\n")
        wait_for(lambda: bool(link.snapshot().error))
        with pytest.raises(RuntimeError, match="fault"):
            diagnostic.observe(link, 1, True)
    finally:
        link.stop()
    assert wire.closed and wire.light == "0"


def test_default_factory_uses_shared_boot_sync_on_com9(monkeypatch):
    wire = LightWire("LIGHT_CONTROLLER")
    original = wire.write
    def write(data):
        if data == b"\n":
            wire.writes.append("STARTUP_DELIMITER")
            wire.emit("ERROR:INVALID_LINE\n")
            return 1
        return original(data)
    wire.write = write
    opening = Mock(return_value=wire)
    monkeypatch.setattr(serial, "Serial", opening)
    monkeypatch.setattr(diagnostic, "observe", Mock())
    assert diagnostic.test_light(diagnostic.arguments([]), prompt=lambda _: "y", output=lambda _: None)
    opening.assert_called_once_with("COM9", 115200, timeout=.02, write_timeout=.2)
    assert wire.writes[0] == "STARTUP_DELIMITER" and wire.closed and wire.light == "0"


@pytest.mark.parametrize("args", [["--seconds", "0"], ["--seconds", "11"], ["--cycles", "0"], ["--cycles", "6"], ["--port", ""]])
def test_invalid_duration_and_cycle_count_rejected_before_connection(args):
    with pytest.raises(SystemExit):
        diagnostic.arguments(args)


def test_check_flag_displays_status_and_never_turns_light_on():
    wire = LightWire("LIGHT_CONTROLLER")
    factory, opened, _ = fixture_link(wire)
    output = []
    assert diagnostic.test_light(diagnostic.arguments(["--check"]), factory=factory,
                                 prompt=lambda _: "y", output=output.append)
    assert opened == ["COM9"] and wire.closed and wire.light == "0"
    assert commands(wire) == ["STATUS"]
    assert any("LIGHT=0" in line and "BUSY=0" in line for line in output)


def test_custom_port_opens_specified_port():
    wire = LightWire("LIGHT_CONTROLLER")
    factory, opened, _ = fixture_link(wire)
    holds = Mock()
    output = []
    assert diagnostic.test_light(diagnostic.arguments(["--port", "COM4", "--cycles", "1"]),
                                 factory=factory, prompt=lambda _: "y", output=output.append)
    assert opened == ["COM4"] and wire.closed and wire.light == "0"

