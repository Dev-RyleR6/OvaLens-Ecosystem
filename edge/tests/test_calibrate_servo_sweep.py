"""Unit tests for the servo angle and reject-sweep calibration CLI."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "edge"))
sys.path.insert(0, str(ROOT / "scripts"))

import calibrate_servo_sweep as cli  # noqa: E402
from src.core.settings import CalibrationSettings  # noqa: E402


def test_compute_reject_plan_matches_edge_cycle_timing():
    cal = CalibrationSettings(
        sorter_steps=367,
        gate_clearance_steps=50,
        speed_us=4000,
        direction=1,
        position_tolerance_steps=5,
        reject_lead_ms=225,
        reject_sweep_ms=450,
    )
    plan = cli.compute_reject_plan(cal)
    assert plan.delta_steps == 417
    assert plan.approach_steps == 338
    assert plan.limit_steps == 367
    assert plan.command == "ADVANCE_REJECT:417:338:367:450"
    assert plan.sweep_start_ms_from_centre < 0
    assert plan.sweep_end_ms_from_centre > 0

    cal_zero = CalibrationSettings(**{**cal.__dict__, "reject_lead_ms": 0})
    zero_plan = cli.compute_reject_plan(cal_zero)
    assert zero_plan.command == "ADVANCE_REJECT:417:367:372:450"

    cal_late = CalibrationSettings(**{**cal.__dict__, "reject_lead_ms": -100})
    late_plan = cli.compute_reject_plan(cal_late)
    assert late_plan.command == "ADVANCE_REJECT:417:379:384:450"


def test_format_timing_summary_warns_when_sweep_finishes_early():
    cal = CalibrationSettings(
        sorter_steps=367,
        gate_clearance_steps=50,
        speed_us=4000,
        reject_lead_ms=600,
        reject_sweep_ms=450,
    )
    summary = cli.format_timing_summary(cal, cli.compute_reject_plan(cal))
    assert "Sweep finishes BEFORE egg reaches gate centre" in summary
    assert "ADVANCE_REJECT:417:292:367:450" in summary
