"""Interactive Servo Angle & Reject-Sweep Calibration CLI for OvaLens Unified ESP32.

Tests individual servo angles, tunes neutral/fertile/infertile presets, and
runs unloaded or 1-egg synchronized conveyor + reject-sweep timing tests using
the exact Edge ThreeBoardCycle step calculations.

Run interactively:
    .venv\\Scripts\\python.exe scripts\\calibrate_servo_sweep.py

Or with flags:
    .venv\\Scripts\\python.exe scripts\\calibrate_servo_sweep.py --angle 115
    .venv\\Scripts\\python.exe scripts\\calibrate_servo_sweep.py --sweep-only --neutral 10 --infertile 115 --sweep-ms 450
    .venv\\Scripts\\python.exe scripts\\calibrate_servo_sweep.py --dry-run --lead-ms 225 --sweep-ms 450
    .venv\\Scripts\\python.exe scripts\\calibrate_servo_sweep.py --feed-egg --lead-ms 225 --sweep-ms 450 --save
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import sys
import time
import serial.tools.list_ports

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "edge"))

from src.core.settings import CalibrationSettings, EdgeSettings, SettingsStore  # noqa: E402
from src.iot.unified_board import UnifiedBoardController, discover_unified_board  # noqa: E402


@dataclass(frozen=True)
class RejectSweepPlan:
    delta_steps: int
    approach_steps: int
    limit_steps: int
    centre_steps: int
    step_ms: float
    lead_steps: int
    sweep_start_ms_from_centre: float
    sweep_end_ms_from_centre: float
    clearance_ms: float
    total_move_ms: float
    command: str
    timeout_s: float


def compute_reject_plan(cal: CalibrationSettings) -> RejectSweepPlan:
    """Compute the exact ADVANCE_REJECT command and human-readable timing metrics."""
    step_us = 2 * cal.speed_us
    step_ms = step_us / 1000.0
    delta = cal.sorter_steps + cal.gate_clearance_steps
    lead_steps = math.ceil(1000 * cal.reject_lead_ms / step_us)
    approach = min(delta - 1, max(1, cal.sorter_steps - lead_steps))
    limit = max(cal.sorter_steps, min(delta - 1, approach + max(1, cal.position_tolerance_steps)))

    actual_lead_steps = cal.sorter_steps - approach
    start_from_centre_ms = -actual_lead_steps * step_ms
    end_from_centre_ms = start_from_centre_ms + cal.reject_sweep_ms
    clearance_ms = cal.gate_clearance_steps * step_ms
    total_move_ms = delta * step_ms

    command = f"ADVANCE_REJECT:{delta * cal.direction}:{approach}:{limit}:{cal.reject_sweep_ms}"
    timeout_s = max(3.0, total_move_ms / 1000.0 + cal.reject_sweep_ms / 1000.0 + 3.0)
    return RejectSweepPlan(
        delta_steps=delta,
        approach_steps=approach,
        limit_steps=limit,
        centre_steps=cal.sorter_steps,
        step_ms=step_ms,
        lead_steps=actual_lead_steps,
        sweep_start_ms_from_centre=start_from_centre_ms,
        sweep_end_ms_from_centre=end_from_centre_ms,
        clearance_ms=clearance_ms,
        total_move_ms=total_move_ms,
        command=command,
        timeout_s=timeout_s,
    )


def format_timing_summary(cal: CalibrationSettings, plan: RejectSweepPlan) -> str:
    start_desc = (
        f"{abs(plan.sweep_start_ms_from_centre):.0f} ms BEFORE gate centre"
        if plan.sweep_start_ms_from_centre < 0
        else f"{plan.sweep_start_ms_from_centre:.0f} ms AFTER gate centre"
        if plan.sweep_start_ms_from_centre > 0
        else "AT gate centre"
    )
    end_desc = (
        f"{abs(plan.sweep_end_ms_from_centre):.0f} ms BEFORE gate centre"
        if plan.sweep_end_ms_from_centre < 0
        else f"{plan.sweep_end_ms_from_centre:.0f} ms AFTER gate centre"
    )
    lines = [
        "--- Calibration & Timing Summary ---",
        f"  Angles        : neutral={cal.neutral_angle} deg, fertile={cal.fertile_angle} deg, infertile={cal.infertile_angle} deg",
        f"  Stepper       : speed_us={cal.speed_us} ({plan.step_ms:.1f} ms/step), dir={cal.direction}",
        f"  Gate geometry : sorter_steps={cal.sorter_steps}, clearance={cal.gate_clearance_steps} ({plan.clearance_ms:.0f} ms)",
        f"  Sweep config  : lead={cal.reject_lead_ms} ms, duration={cal.reject_sweep_ms} ms",
        f"  Sweep window  : starts {start_desc} (step {plan.approach_steps}/{plan.centre_steps}) -> finishes {end_desc}",
        f"  Command       : {plan.command}",
    ]
    if plan.sweep_end_ms_from_centre < 0:
        lines.append("  [NOTE] Sweep finishes BEFORE egg reaches gate centre; lower reject_lead_ms to sweep the egg.")
    elif plan.sweep_end_ms_from_centre > plan.clearance_ms:
        lines.append("  [NOTE] Belt reaches gate exit before sweep finishes; it will pause briefly at exit to finish.")
    return "\n".join(lines)


def resolve_port(port_override: str, settings: EdgeSettings) -> str:
    if port_override:
        return port_override
    preferred = tuple(p for p in (settings.conveyor_port, "COM5", "COM7", "COM9", "COM3", "COM4") if p)
    try:
        return discover_unified_board(preferred=preferred, timeout=2.5)
    except Exception:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if settings.conveyor_port and settings.conveyor_port in ports:
            return settings.conveyor_port
        if ports:
            return ports[0]
        raise


def connect_board(port: str) -> UnifiedBoardController:
    print(f"Connecting to Unified ESP32 on {port}...")
    ctrl = UnifiedBoardController(port)
    ctrl.start()
    deadline = time.monotonic() + 5.0
    while True:
        state = ctrl.link.snapshot()
        if state.error or time.monotonic() >= deadline:
            ctrl.stop()
            raise RuntimeError(state.error or f"Timed out connecting on {port}")
        if ctrl.link._status_complete and state.telemetry.get("BUSY") == "0":
            break
        time.sleep(0.05)

    state = ctrl.link.snapshot()
    if state.telemetry.get("REJECT_SWEEP") != "3":
        ctrl.stop()
        raise RuntimeError("ESP32 firmware does not report REJECT_SWEEP:3. Flash unified_ovalens.ino first.")
    if state.telemetry.get("FAULT", "NONE") != "NONE":
        ctrl.link.command("ACK_FAULT").result(3.5)
    ctrl.link.command("LIGHT_OFF").result(3.5)
    ctrl.link.command("PAUSE").result(3.5)
    print(f"[CONNECTED] {port} ready (ANGLE={ctrl.link.snapshot().telemetry.get('ANGLE')} deg).\n")
    return ctrl


def sync_presets(ctrl: UnifiedBoardController, cal: CalibrationSettings) -> None:
    ctrl.link.command(f"SPEED:{cal.speed_us}").result(3.5)
    ctrl.link.command(f"SET_NEUTRAL:{cal.neutral_angle}").result(3.5)
    ctrl.link.command(f"SET_FERTILE:{cal.fertile_angle}").result(3.5)
    ctrl.link.command(f"SET_INFERTILE:{cal.infertile_angle}").result(3.5)


def move_to_angle(ctrl: UnifiedBoardController, angle: int) -> int:
    if not 0 <= angle <= 180:
        raise ValueError("Angle must be between 0 and 180")
    res = ctrl.link.command(f"SERVO:{angle}", timeout=4.0).result(4.5)
    actual = int(res.get("ANGLE", angle))
    print(f"  -> Servo at {actual} deg")
    return actual


def test_sweep_only(ctrl: UnifiedBoardController, cal: CalibrationSettings, pause_s: float = 0.5) -> None:
    sync_presets(ctrl, cal)
    print(f">>> Sweeping to neutral ({cal.neutral_angle} deg)...")
    ctrl.link.command("RESET", timeout=4.0).result(4.5)
    time.sleep(pause_s)
    print(f">>> Sweeping to infertile ({cal.infertile_angle} deg)...")
    ctrl.link.command("SORT:INFERTILE", timeout=4.0).result(4.5)
    time.sleep(pause_s)
    print(f">>> Sweeping back to neutral ({cal.neutral_angle} deg)...")
    ctrl.link.command("RESET", timeout=4.0).result(4.5)
    print(">>> Sweep-only test complete.")


def run_reject_sweep(ctrl: UnifiedBoardController, cal: CalibrationSettings, feed_egg: bool = False) -> None:
    plan = compute_reject_plan(cal)
    print(format_timing_summary(cal, plan))

    sync_presets(ctrl, cal)
    print(">>> Moving gate to neutral...")
    ctrl.link.command("RESET", timeout=4.0).result(4.5)

    snap = ctrl.link.snapshot()
    if snap.telemetry.get("SENSOR") != "0":
        raise RuntimeError("Chamber IR sensor is blocked. Clear the chamber before starting.")

    ctrl.link.command("SETHOME").result(3.5)
    ctrl.link.command("ARM").result(3.5)
    origin = 0

    try:
        if feed_egg:
            print(f">>> Conveyor searching up to {cal.holder_steps} steps — place ONE egg onto the belt before the IR chamber...")
            ctrl.link.command("RESUME").result(3.5)
            search_timeout = max(5.0, cal.holder_steps * plan.step_ms / 1000.0 + 3.0)
            search_reply = ctrl.link.command(f"ADVANCE:{cal.holder_steps * cal.direction}", timeout=search_timeout).result(search_timeout + 0.5)
            state = search_reply.get("STATE")
            paused = search_reply.get("PAUSED")
            origin = int(search_reply.get("POSITION", "0"))
            if state != "HOLDING" or paused != "1":
                raise RuntimeError(f"No egg detected at IR chamber (STATE={state}, PAUSED={paused}).")
            print(f">>> Egg held at chamber position {origin}. Pausing 0.5s before reject sweep...")
            time.sleep(0.5)

        print(">>> Running ADVANCE_REJECT...")
        ctrl.link.command("RESUME").result(3.5)
        t0 = time.monotonic()
        reply = ctrl.link.command(plan.command, timeout=plan.timeout_s).result(plan.timeout_s + 0.5)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        reject_at = (int(reply.get("REJECT_AT", "0")) - origin) * cal.direction
        final_pos = (int(reply.get("POSITION", "0")) - origin) * cal.direction
        print(
            f">>> ADVANCE_REJECT done in {elapsed_ms:.0f} ms: "
            f"POSITION={final_pos} (target {plan.delta_steps}), "
            f"REJECT_AT={reject_at} (planned {plan.approach_steps}, centre {plan.centre_steps}), "
            f"ANGLE={reply.get('ANGLE')} deg"
        )
        print(f">>> Sweeping gate back to neutral ({cal.neutral_angle} deg) over {cal.reject_sweep_ms} ms...")
        ctrl.link.command("RESET", timeout=4.0).result(4.5)
    finally:
        try:
            ctrl.link.command("PAUSE").result(2.0)
        except Exception:
            pass


def jog_stepper(ctrl: UnifiedBoardController, cal: CalibrationSettings, steps: int) -> None:
    if steps == 0 or abs(steps) > 100000:
        raise ValueError("Steps must be nonzero and within +/-100000")
    ctrl.link.command(f"SPEED:{cal.speed_us}").result(3.5)
    ctrl.link.command("RESUME").result(3.5)
    try:
        timeout = 3.0 + abs(steps) * (2 * cal.speed_us / 1_000_000.0)
        res = ctrl.link.command(f"JOG:{steps}", timeout=timeout).result(timeout + 0.5)
        print(f"  -> Position is now {res.get('POSITION')}")
    finally:
        try:
            ctrl.link.command("PAUSE").result(2.0)
        except Exception:
            pass


def save_settings(store: SettingsStore, settings: EdgeSettings) -> None:
    settings.validate()
    store.save(settings)
    print(f"[SAVED] Calibration saved to {store.path}")


def prompt_int(prompt_text: str, current: int, lo: int, hi: int) -> int:
    raw = input(f"{prompt_text} [{current}] ({lo}..{hi}): ").strip()
    if not raw:
        return current
    val = int(raw)
    if not lo <= val <= hi:
        raise ValueError(f"Value must be between {lo} and {hi}")
    return val


def interactive_loop(ctrl: UnifiedBoardController, settings: EdgeSettings, store: SettingsStore) -> None:
    cal = settings.calibration
    current_angle = int(ctrl.link.snapshot().telemetry.get("ANGLE") or cal.neutral_angle)

    def show_help() -> None:
        print(
            f"""
====================================================================
      OvaLens Servo Angle & Sweep Calibration CLI
====================================================================
  Current Angle : {current_angle} deg
  Presets       : neutral={cal.neutral_angle}, fertile={cal.fertile_angle}, infertile={cal.infertile_angle}
  Sweep Timing  : lead={cal.reject_lead_ms} ms, duration={cal.reject_sweep_ms} ms, speed_us={cal.speed_us}
--------------------------------------------------------------------
  Angle testing:
    <0..180>   Move servo immediately to exact angle (e.g. 115)
    + / -      Nudge +5 / -5 deg  (++ / -- for +1 / -1 deg)
    sn / sf / si   Save current angle as neutral / fertile / infertile
    n  / f  / i    Test preset angle (neutral / fertile / infertile)

  Sweep & timing calibration:
    t          Test servo-only sweep (neutral -> infertile -> neutral)
    r          Dry-run conveyor + ADVANCE_REJECT sweep (unloaded belt)
    e          Live 1-egg test (IR stop in chamber -> ADVANCE_REJECT)
    l          Set reject_lead_ms (-500..1500; 0=at centre, 225=centered)
    d          Set reject_sweep_ms (80..1000)
    g          Edit sorter_steps / gate_clearance_steps / speed_us
    j <steps>  Jog stepper (e.g. j 100 or j -100)
    p          Print timing summary
    s          Save calibration to {store.path.name}
    h / q      Help / Quit
====================================================================
"""
        )

    show_help()
    while True:
        try:
            raw = input("calibrate> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not raw:
            continue
        cmd = raw.lower()
        try:
            if cmd in {"q", "quit", "exit"}:
                break
            elif cmd in {"h", "help", "?"}:
                show_help()
            elif cmd == "p":
                print(format_timing_summary(cal, compute_reject_plan(cal)))
            elif cmd.lstrip("-").isdigit() and not raw.startswith(("+", "-")):
                current_angle = move_to_angle(ctrl, int(raw))
            elif cmd == "+":
                current_angle = move_to_angle(ctrl, min(180, current_angle + 5))
            elif cmd == "-":
                current_angle = move_to_angle(ctrl, max(0, current_angle - 5))
            elif cmd == "++":
                current_angle = move_to_angle(ctrl, min(180, current_angle + 1))
            elif cmd == "--":
                current_angle = move_to_angle(ctrl, max(0, current_angle - 1))
            elif cmd == "sn":
                cal.neutral_angle = current_angle
                settings.validate()
                sync_presets(ctrl, cal)
                print(f"  -> neutral_angle set to {cal.neutral_angle} deg")
            elif cmd == "sf":
                cal.fertile_angle = current_angle
                settings.validate()
                sync_presets(ctrl, cal)
                print(f"  -> fertile_angle set to {cal.fertile_angle} deg")
            elif cmd == "si":
                cal.infertile_angle = current_angle
                settings.validate()
                sync_presets(ctrl, cal)
                print(f"  -> infertile_angle set to {cal.infertile_angle} deg")
            elif cmd == "n":
                current_angle = move_to_angle(ctrl, cal.neutral_angle)
            elif cmd == "f":
                current_angle = move_to_angle(ctrl, cal.fertile_angle)
            elif cmd == "i":
                current_angle = move_to_angle(ctrl, cal.infertile_angle)
            elif cmd == "t":
                test_sweep_only(ctrl, cal)
                current_angle = cal.neutral_angle
            elif cmd == "r":
                run_reject_sweep(ctrl, cal, feed_egg=False)
                current_angle = cal.neutral_angle
            elif cmd == "e":
                run_reject_sweep(ctrl, cal, feed_egg=True)
                current_angle = cal.neutral_angle
            elif cmd == "l":
                cal.reject_lead_ms = prompt_int("Reject sweep lead before gate centre (ms)", cal.reject_lead_ms, -500, 1500)
                settings.validate()
                print(format_timing_summary(cal, compute_reject_plan(cal)))
            elif cmd == "d":
                cal.reject_sweep_ms = prompt_int("Reject sweep duration (ms)", cal.reject_sweep_ms, 80, 1000)
                settings.validate()
                print(format_timing_summary(cal, compute_reject_plan(cal)))
            elif cmd == "g":
                cal.sorter_steps = prompt_int("Chamber to gate centre (steps)", cal.sorter_steps, 2, 1000000)
                cal.gate_clearance_steps = prompt_int("Gate clearance (steps)", cal.gate_clearance_steps, 1, cal.holder_steps // 2 - 1)
                cal.speed_us = prompt_int("Stepper half-period (us)", cal.speed_us, 200, 5000)
                settings.validate()
                print(format_timing_summary(cal, compute_reject_plan(cal)))
            elif cmd.startswith("j "):
                jog_stepper(ctrl, cal, int(cmd.split(None, 1)[1]))
            elif cmd == "s":
                save_settings(store, settings)
            else:
                print("  [!] Unknown command. Type 'h' for help.")
        except Exception as exc:
            print(f"  [!] {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calibrate OvaLens unified servo angles and reject sweep timing")
    parser.add_argument("--port", default="", help="Serial port override (default: from edge_settings.json or auto-discover)")
    parser.add_argument("--settings", default="", help="Optional path to edge_settings.json")
    parser.add_argument("--angle", type=int, default=None, help="Move servo to a single angle (0-180) and exit")
    parser.add_argument("--neutral", type=int, default=None, help="Override neutral_angle (0-180)")
    parser.add_argument("--fertile", type=int, default=None, help="Override fertile_angle (0-180)")
    parser.add_argument("--infertile", type=int, default=None, help="Override infertile_angle (0-180)")
    parser.add_argument("--lead-ms", type=int, default=None, help="Override reject_lead_ms (-500..1500)")
    parser.add_argument("--sweep-ms", type=int, default=None, help="Override reject_sweep_ms (80..1000)")
    parser.add_argument("--sweep-only", action="store_true", help="Sweep neutral -> infertile -> neutral without moving belt")
    parser.add_argument("--dry-run", action="store_true", help="Run unloaded conveyor + ADVANCE_REJECT sweep")
    parser.add_argument("--feed-egg", action="store_true", help="Wait for 1 egg at IR chamber, then run ADVANCE_REJECT sweep")
    parser.add_argument("--save", action="store_true", help="Save overridden calibration values to edge_settings.json")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    store = SettingsStore(args.settings or None)
    settings = store.load()
    cal = settings.calibration

    if args.neutral is not None:
        cal.neutral_angle = args.neutral
    if args.fertile is not None:
        cal.fertile_angle = args.fertile
    if args.infertile is not None:
        cal.infertile_angle = args.infertile
    if args.lead_ms is not None:
        cal.reject_lead_ms = args.lead_ms
    if args.sweep_ms is not None:
        cal.reject_sweep_ms = args.sweep_ms
    settings.validate()

    port = resolve_port(args.port, settings)
    ctrl = None
    try:
        ctrl = connect_board(port)
        if args.angle is not None:
            move_to_angle(ctrl, args.angle)
        elif args.sweep_only:
            test_sweep_only(ctrl, cal)
        elif args.dry_run:
            run_reject_sweep(ctrl, cal, feed_egg=False)
        elif args.feed_egg:
            run_reject_sweep(ctrl, cal, feed_egg=True)
        else:
            interactive_loop(ctrl, settings, store)
            return 0

        if args.save:
            save_settings(store, settings)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        if ctrl is not None:
            try:
                ctrl.stop()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
