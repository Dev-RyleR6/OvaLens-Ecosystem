r"""One short COM5 jog using the installed three-board v3 firmware.

Run from the repository root with .venv\Scripts\python.exe scripts\test_stepper.py.
Only the chosen conveyor port is opened. Hardware pause is never overridden.
"""
import argparse
from pathlib import Path
import sys
import time


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM5", help="Conveyor ESP32 port (default: COM5)")
    parser.add_argument("--steps", type=int, default=50, help="Signed relative steps, -1000..1000 excluding 0 (default: 50)")
    parser.add_argument("--speed-us", type=int, default=5000,
                        help="Pulse half-period, 200..5000 us; higher is slower (default: 5000)")
    parser.add_argument("--check", action="store_true", help="Identify and display status without a jog or fault acknowledgement")
    args = parser.parse_args(argv)
    if not args.port.strip():
        parser.error("Choose a conveyor serial port.")
    if args.steps == 0 or abs(args.steps) > 1000:
        parser.error("--steps must be -1000..1000 and cannot be zero.")
    if not 200 <= args.speed_us <= 5000:
        parser.error("--speed-us must be 200..5000 (higher is slower).")
    args.port = args.port.strip()
    return args


def idle_status(status):
    if status.get("BUSY") != "0":
        raise RuntimeError("Conveyor is busy or status is incomplete. Stop it before testing.")
    if status.get("PAUSED") != "0":
        raise RuntimeError("Hardware pause is active (GPIO27). COM7 controls this signal. "
                           "This COM5-only test cannot release it and will not bypass it.")
    try:
        return int(status["POSITION"])
    except (KeyError, ValueError, TypeError):
        raise RuntimeError("Conveyor did not report a valid position.") from None


def test_stepper(args, *, factory=None, prompt=input, output=print):
    """Dependency injection supports byte-level hardware-free tests."""
    if factory is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge"))
        from src.iot.dual_board import BoardLink
        factory = BoardLink
    output(f"Conveyor only: {args.port}, 115200 baud, three-board v3 firmware.")
    output("Close OvaLens Edge and Arduino Serial Monitor first. Opening the port may reset the conveyor controller.")
    if not args.check:
        answer = prompt(f"Empty the conveyor and clear the path. Move {args.steps} steps at {args.speed_us} us? [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            output("Cancelled. No serial port opened.")
            return False
    link = factory("CONVEYOR", args.port, protocol=3)
    try:
        link.start()
        deadline = time.monotonic() + 6
        while not link._status_complete:
            state = link.snapshot()
            if state.error or time.monotonic() >= deadline:
                raise RuntimeError(state.error or "Conveyor identification timed out. Check COM5 and v3 firmware.")
            time.sleep(.02)
        status = link.command("STATUS").result(3.5)
        output(" | ".join(f"{key}={status.get(key, '?')}" for key in ("FAULT", "BUSY", "PAUSED", "POSITION", "SPEED")))
        if args.check:
            return True
        start = idle_status(status)
        fault = status.get("FAULT")
        if fault not in {"NONE", "STARTUP_ACK_REQUIRED", "EMERGENCY_STOP", "LINK_TIMEOUT"}:
            raise RuntimeError(f"Inspect controller fault {fault!r} before testing.")
        if fault != "NONE":
            reply = link.command("ACK_FAULT").result(3.5)
            if reply.get("FAULT") != "NONE":
                raise RuntimeError("Controller did not acknowledge the inspected fault.")
        speed = link.command(f"SPEED:{args.speed_us}").result(3.5)
        if speed.get("SPEED") != str(args.speed_us):
            raise RuntimeError("Controller did not confirm the requested speed.")
        # Recheck pause and position immediately before dispatching a finite jog.
        if idle_status(link.command("STATUS").result(3.5)) != start:
            raise RuntimeError("Position changed before the test. Inspect the conveyor.")
        timeout = 3 + abs(args.steps) * 2 * args.speed_us / 1_000_000
        output("Moving. Press Ctrl+C to stop.")
        reply = link.command(f"JOG:{args.steps}", timeout=timeout).result(timeout + .5)
        if reply.get("FAULT") != "NONE" or reply.get("BUSY") != "0" or reply.get("POSITION") != str(start + args.steps):
            raise RuntimeError("Move stopped early or completion did not match the requested steps. No retry issued.")
        output(f"Controller completed {args.steps} steps: {start} -> {reply['POSITION']}. "
               "Check that the motor physically moved smoothly.")
        return True
    finally:
        link.stop()  # BoardLink sends ESTOP and closes its port, including on Ctrl+C/error.
        output("Stop requested and port closed. Inspect the conveyor; Prepare station again before sorting.")


test_stepper.__test__ = False  # This hardware diagnostic is not a pytest test.


def main(argv=None):
    args = arguments(argv)
    try:
        return 0 if test_stepper(args) else 1
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C.")
        return 130
    except Exception as exc:
        print("Test stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
