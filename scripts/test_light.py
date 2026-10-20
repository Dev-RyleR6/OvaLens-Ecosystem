r"""Test the COM9 lamp with the installed three-board v3 firmware.

From scripts/: python test_light.py
Default: light ON for two seconds, OFF for one second, repeat twice.
COM5 and COM7 are never opened. No camera or IR sensor is needed.
"""
import argparse
from pathlib import Path
import sys
import time


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM9", help="Light controller serial port (default: COM9)")
    parser.add_argument("--seconds", type=int, default=2, help="ON time per cycle, 1-10 seconds (default: 2)")
    parser.add_argument("--cycles", type=int, default=2, help="Number of ON/OFF cycles, 1-5 (default: 2)")
    parser.add_argument("--check", action="store_true", help="Display controller status without switching the light on")
    args = parser.parse_args(argv)
    if not args.port.strip():
        parser.error("Choose a light controller serial port.")
    if not 1 <= args.seconds <= 10:
        parser.error("--seconds must be 1-10 (below the lamp's 15-second auto-off limit).")
    if not 1 <= args.cycles <= 5:
        parser.error("--cycles must be 1-5.")
    args.port = args.port.strip()
    return args


def require_output(status, expected):
    if status.get("BUSY") != "0" or status.get("LIGHT") != str(int(expected)):
        raise RuntimeError("Light controller did not confirm the requested output. Test stopped.")


def observe(link, seconds, expected):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        state = link.snapshot()
        if state.error or state.telemetry.get("FAULT") != "NONE":
            raise RuntimeError(state.error or "Light controller faulted. No ON retry issued.")
        require_output(state.telemetry, expected)
        time.sleep(min(.05, max(0, deadline - time.monotonic())))


def test_light(args, *, factory=None, prompt=input, output=print):
    output(f"Light test on {args.port} only. COM5 and COM7 stay unopened. No sensor needed.")
    output("Close OvaLens Edge and Arduino Serial Monitor before connecting.")
    description = "check status" if args.check else f"switch the light ON/OFF {args.cycles} times"
    if prompt(f"Connect to {args.port} and {description}? [y/N] ").strip().lower() not in {"y", "yes"}:
        output("Cancelled. No serial port opened.")
        return False
    if factory is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge"))
        from src.iot.dual_board import BoardLink
        from src.iot.diagnostic_serial import open_diagnostic_port
        def factory(*f_args, **f_kwargs):
            def open_port(*port_args, **port_options):
                return open_diagnostic_port(*port_args, stop_event=link._stop, **port_options)
            link = BoardLink(*f_args, serial_factory=open_port, **f_kwargs)
            return link
        output(f"Waiting for {args.port} to boot, then checking the light controller...")
    link = factory("LIGHT_CONTROLLER", args.port, protocol=3)
    try:
        link.start()
        deadline = time.monotonic() + 6
        while not link._status_complete:
            state = link.snapshot()
            if state.error or time.monotonic() >= deadline:
                raise RuntimeError(state.error or f"Light identification timed out. Check {args.port} and v3 firmware.")
            time.sleep(.02)
        status = link.command("STATUS").result(3.5)
        if args.check:
            output(" | ".join(f"{key}={status.get(key, '?')}" for key in ("FAULT", "BUSY", "LIGHT", "STATE")))
            return True
        require_output(status, False)
        if status.get("FAULT") not in {"NONE", "STARTUP_ACK_REQUIRED", "EMERGENCY_STOP", "LINK_TIMEOUT", "LIGHT_AUTO_OFF_TIMEOUT"}:
            raise RuntimeError(f"Inspect light controller fault {status.get('FAULT')!r} before testing.")
        if status["FAULT"] != "NONE":
            status = link.command("ACK_FAULT").result(3.5)
            require_output(status, False)
        if status.get("FAULT") != "NONE":
            raise RuntimeError("Controller did not acknowledge the inspected fault.")
        for cycle in range(1, args.cycles + 1):
            status = link.command("LIGHT_ON").result(3.5)
            require_output(status, True)
            if status.get("FAULT") != "NONE":
                raise RuntimeError("Controller faulted while turning the light on.")
            output(f"{cycle}/{args.cycles}: Light ON ({args.seconds}s)")
            observe(link, args.seconds, True)
            status = link.command("LIGHT_OFF").result(3.5)
            require_output(status, False)
            if status.get("FAULT") != "NONE":
                raise RuntimeError("Controller faulted while turning the light off.")
            output(f"{cycle}/{args.cycles}: Light OFF")
            if cycle < args.cycles:
                observe(link, 1, False)
        output("Done. Observe the actual lamp; controller feedback confirms the commanded output only.")
        return True
    finally:
        link.stop()  # Uncorrelated ESTOP turns the lamp off, even during a fault.
        output(f"OFF/stop requested; {args.port} closed.")


test_light.__test__ = False


def main(argv=None):
    try:
        return 0 if test_light(arguments(argv)) else 1
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C.")
        return 130
    except Exception as exc:
        print("Test stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
