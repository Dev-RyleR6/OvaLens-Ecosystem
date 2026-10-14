r"""Test the COM7 sorting servo using the installed three-board v3 firmware.

Run .venv\Scripts\python.exe scripts\test_servo.py from the repository root.
Default sequence: 90 -> 120 -> 90 degrees. No IR sensor is needed.
COM5 and COM9 are never opened.
Opening COM7 may reset its ESP32 and move the servo to its boot angle (90).
"""
import argparse
from pathlib import Path
import sys
import time


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--angles", nargs="+", type=int, default=[90, 120, 90],
                        help="1-10 angles, each 0-180 degrees (default: 90 120 90)")
    parser.add_argument("--hold-ms", type=int, default=1000,
                        help="Observation time between confirmed positions, 0-5000 ms (default: 1000)")
    parser.add_argument("--check", action="store_true", help="Display controller status without sending an angle command; connection may still cause a boot movement")
    args = parser.parse_args(argv)
    if not 1 <= len(args.angles) <= 10 or any(not 0 <= angle <= 180 for angle in args.angles):
        parser.error("Provide 1-10 angles between 0 and 180 degrees.")
    if not 0 <= args.hold_ms <= 5000:
        parser.error("--hold-ms must be 0-5000.")
    return args


def safe_status(status):
    if status.get("BUSY") != "0":
        raise RuntimeError("Servo is busy or status is incomplete.")
    if status.get("PAUSED") != "1":
        raise RuntimeError("Conveyor hold is not confirmed. No servo movement requested.")
    try:
        angle = int(status["ANGLE"])
    except (KeyError, ValueError, TypeError):
        raise RuntimeError("Servo did not report a valid angle.") from None
    if not 0 <= angle <= 180:
        raise RuntimeError("Servo reported an angle outside 0-180 degrees.")
    return angle


def test_servo(args, *, factory=None, prompt=input, output=print):
    output("Servo test on COM7. No IR sensor needed. COM5 and COM9 stay unopened.")
    output("Close OvaLens Edge and Arduino Serial Monitor. Opening COM7 can move the servo to its boot angle (90 degrees).")
    description = "check status" if args.check else "test angles " + " -> ".join(map(str, args.angles))
    answer = prompt(f"Clear the servo's movement path. Connect and {description}? [y/N] ")
    if answer.strip().lower() not in {"y", "yes"}:
        output("Cancelled. No serial port opened.")
        return False
    if factory is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge"))
        from src.iot.dual_board import BoardLink
        factory = BoardLink
    link = factory("EGG_CONTROLLER", "COM7", protocol=3)
    try:
        link.start()
        deadline = time.monotonic() + 6
        # A resetting servo normally reports BUSY during its 500 ms boot settle.
        while not link._status_complete or link.snapshot().telemetry.get("BUSY") != "0":
            state = link.snapshot()
            if state.error or time.monotonic() >= deadline:
                raise RuntimeError(state.error or "Servo identification/boot settling timed out. Check COM7 and v3 firmware.")
            time.sleep(.02)
        status = link.command("STATUS").result(3.5)
        if args.check:
            output(" | ".join(f"{key}={status.get(key, '?')}" for key in ("FAULT", "BUSY", "PAUSED", "ANGLE")))
            return True
        safe_status(status)
        fault = status.get("FAULT")
        if fault not in {"NONE", "STARTUP_ACK_REQUIRED", "EMERGENCY_STOP", "LINK_TIMEOUT"}:
            raise RuntimeError(f"Inspect servo controller fault {fault!r} before testing.")
        if fault != "NONE" and link.command("ACK_FAULT").result(3.5).get("FAULT") != "NONE":
            raise RuntimeError("Controller did not acknowledge the inspected fault.")
        held = link.command("PAUSE").result(3.5)
        safe_status(held)
        if held.get("FAULT") != "NONE":
            raise RuntimeError("Servo controller is faulted. No angle command sent.")
        for index, angle in enumerate(args.angles):
            status = link.command("STATUS").result(3.5)
            safe_status(status)
            if status.get("FAULT") != "NONE":
                raise RuntimeError("Controller faulted before movement. No retry issued.")
            output(f"Moving to {angle} degrees. Ctrl+C stops the test.")
            reply = link.command(f"SERVO:{angle}").result(3.5)
            actual = safe_status(reply)
            if reply.get("FAULT") != "NONE" or actual != angle:
                raise RuntimeError("Servo completion did not match the requested position. No retry issued.")
            if index < len(args.angles) - 1:
                # The serial worker continues heartbeat/status traffic during observation.
                deadline = time.monotonic() + args.hold_ms / 1000
                while time.monotonic() < deadline:
                    state = link.snapshot()
                    safe_status(state.telemetry)
                    if state.error or state.telemetry.get("FAULT") != "NONE":
                        raise RuntimeError(state.error or "Servo controller faulted while holding.")
                    time.sleep(min(.05, max(0, deadline - time.monotonic())))
        output("Done. If the servo moved back and forth, it is responding. Reported angles do not prove physical movement.")
        return True
    finally:
        link.stop()  # Requests ESTOP (holds pause/current angle) and closes COM7.
        output("Stop requested; COM7 closed. Inspect the gate and Prepare station again before sorting.")


test_servo.__test__ = False


def main(argv=None):
    args = arguments(argv)
    try:
        return 0 if test_servo(args) else 1
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C. No further angle commands requested.")
        return 130
    except Exception as exc:
        print("Test stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
