"""TASK-NEW-EDGE-PAUSE-01: same-session pause with simulated hardware only."""
from unittest.mock import Mock
from pathlib import Path
import threading
import time

import pytest

from test_three_board import fixture, wait_for
from test_camera_preview_ui import preview_app
from test_startup_config import hidden_ui
from test_live_camera_ui import pump
from src.core.operator_cues import cycle_cue


def pause_on_capture(cycle):
    capture = cycle._capture
    def requested():
        cycle.request_pause()
        return capture()
    cycle._capture = requested


def finish(cycle):
    cycle.stop()
    cycle._thread.join(2)
    assert not cycle.active


def test_repeated_pause_preserves_session_gate_images_counts_and_sequences(tmp_path):
    cycle, db, rig = fixture(tmp_path)
    capture = cycle._capture
    def saved_capture():
        cycle.pending_capture["image_path"] = db.save_scan_image(
            cycle.pending_capture["scan_id"], cycle.camera.snapshot().image)
        cycle.request_pause()
        return capture()
    cycle._capture = saved_capture
    cycle.start()
    try:
        for number, angle in ((1, "180"), (2, "120")):
            wait_for(lambda: cycle.status["state"] == "PAUSED" and cycle.count == number)
            checkpoint = db.load_machine_state("station")
            assert checkpoint["state"] == "PAUSED" and checkpoint["count"] == number
            assert checkpoint["gate_holder"] == number and checkpoint["pause"]["events"]
            assert checkpoint["session_id"] == cycle.session_id
            stats = db.get_session_stats(cycle.session_id)
            assert stats["total_scanned"] == number and not stats["ended_at"]
            assert rig.egg.values["ANGLE"] == angle and rig.egg.values["PAUSED"] == "1"
            assert rig.conveyor.values["PAUSED"] == "1" and rig.light.values["LIGHT"] == "0"
            position, commands = rig.position, len(rig.trace)
            time.sleep(.08)
            assert rig.position == position and len(rig.trace) == commands
            images = [Path(row["image_path"]) for row in db.get_uncommitted_scans()]
            assert len(images) == number and all(path.is_file() for path in images)
            cycle.resume()
        cycle._thread.join(2)
        assert cycle.status["state"] == "COMPLETE", cycle.status
        assert cycle.count == cycle.routed == 2
        assert db.get_session_stats(cycle.session_id)["ended_at"]
        scans = db.get_uncommitted_scans()
        assert {row["session_id"] for row in scans} == {cycle.session_id}
        assert sorted(row["sequence_number"] for row in scans) == [1, 2]
        assert len({row["scan_id"] for row in scans}) == 2
        assert sum(text == "ARM" for _, text, *_ in rig.trace) == 1
    finally:
        finish(cycle)


@pytest.mark.parametrize("change", ["position", "sequence", "sensor", "angle", "pause", "light", "camera", "fault"])
def test_changed_paused_rig_never_releases_saved_egg(tmp_path, change):
    cycle, db, rig = fixture(tmp_path, count=1)
    pause_on_capture(cycle)
    cycle.start()
    try:
        wait_for(lambda: cycle.status["state"] == "PAUSED")
        command_count = len(rig.trace)
        if change == "position":
            rig.conveyor.values["POSITION"] = "999"
        elif change == "sequence":
            rig.egg.values["EGG_SEQ"] = "2"
        elif change == "sensor":
            rig.egg.values["SENSOR"] = "0"
        elif change == "angle":
            rig.egg.values["ANGLE"] = "90"
        elif change == "pause":
            rig.conveyor.values["PAUSED"] = "0"
        elif change == "light":
            rig.light.values["LIGHT"] = "1"
        elif change == "camera":
            cycle.camera.settings_revision += 1
        else:
            rig.egg.values["FAULT"] = "WATCHDOG"
        # Both the paused monitor and resume validation must fail closed.
        if cycle.status["state"] == "PAUSED":
            cycle.resume()
        cycle._thread.join(2)
        assert cycle.status["state"] == "RECOVERY_REQUIRED", cycle.status
        assert not any(text == "RESUME" or text.startswith("ADVANCE:")
                       for _, text, *_ in rig.trace[command_count:])
        assert db.get_session_stats(cycle.session_id)["total_scanned"] == 1
        assert not db.get_session_stats(cycle.session_id)["ended_at"]
        assert db.load_machine_state("station")["state"] == "RECOVERY_REQUIRED"
    finally:
        finish(cycle)


def test_stop_wakes_paused_worker_and_keeps_scans(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1)
    pause_on_capture(cycle)
    cycle.start()
    wait_for(lambda: cycle.status["state"] == "PAUSED")
    finish(cycle)
    assert cycle.status["state"] == "RECOVERY_REQUIRED"
    assert db.get_unsynced_count() == 1
    assert rig.egg.values["PAUSED"] == "1" and rig.light.values["LIGHT"] == "0"
    with pytest.raises(RuntimeError):
        cycle.resume()


@pytest.mark.parametrize("failure", ["ack", "journal"])
def test_pause_requires_ack_and_durable_checkpoint(tmp_path, failure):
    cycle, db, rig = fixture(tmp_path, count=1)
    pause_on_capture(cycle)
    if failure == "ack":
        rig.fail_command = ("EGG_CONTROLLER", "PAUSE")
    else:
        checkpoint = cycle._checkpoint
        def failed(state):
            if state == "PAUSED":
                raise OSError("disk full")
            checkpoint(state)
        cycle._checkpoint = failed
    cycle.start()
    cycle._thread.join(2)
    assert cycle.status["state"] == "RECOVERY_REQUIRED", cycle.status
    assert db.get_unsynced_count() == 1
    assert sum(text == "RESUME" for _, text, *_ in rig.trace) == 1  # Initial arm only.


def test_search_pause_excludes_operator_wait_from_jam_deadline(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1, arrivals=[1700])
    cycle.settings.calibration.jam_timeout_s = 1
    advance = cycle._advance
    def request(destination):
        detected = advance(destination)
        if not detected and cycle.travel < 1700:
            cycle.request_pause()
        return detected
    cycle._advance = request
    cycle.start()
    try:
        wait_for(lambda: cycle.status["state"] == "PAUSED")
        assert cycle.count == 0 and not cycle._pause_context["was_paused"]
        time.sleep(1.1)
        assert cycle.status["state"] == "PAUSED"
        cycle.resume()
        cycle._thread.join(2)
        assert cycle.status["state"] == "COMPLETE", cycle.status
        assert db.get_session_stats(cycle.session_id)["total_scanned"] == 1
    finally:
        finish(cycle)


def test_request_during_movement_waits_for_ack_before_pause(tmp_path):
    cycle, db, rig = fixture(tmp_path, count=1)
    entered, release = threading.Event(), threading.Event()
    command = rig.conveyor.command
    def blocked(text, timeout=3):
        if text.startswith("ADVANCE:") and not entered.is_set():
            entered.set()
            assert release.wait(2)
        return command(text, timeout)
    rig.conveyor.command = blocked
    cycle.start()
    try:
        assert entered.wait(2)
        cycle.request_pause()
        assert cycle.status["state"] != "PAUSED"
        assert not any(text == "PAUSE" for _, text, *_ in rig.trace)
        release.set()
        wait_for(lambda: cycle.status["state"] == "PAUSED")
        assert cycle.count == 1 and rig.egg.values["ANGLE"] == "180"
        cycle.resume()
        cycle._thread.join(2)
        assert cycle.status["state"] == "COMPLETE"
    finally:
        release.set()
        finish(cycle)


def test_native_pause_resume_controls_preserve_current_session(hidden_ui, tmp_path):
    app, _, _ = preview_app(tmp_path)
    cycle, db, rig = fixture(tmp_path / "cycle", count=1)
    # Hold the first advance to exercise the pending state through the actual button.
    entered, release = threading.Event(), threading.Event()
    command = rig.conveyor.command
    def blocked(text, timeout=3):
        if text.startswith("ADVANCE:") and not entered.is_set():
            entered.set()
            assert release.wait(3)
        return command(text, timeout)
    rig.conveyor.command = blocked
    app.station.cycle = cycle
    app.db = db
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        app.deiconify()
        cycle.start()
        assert entered.wait(2)
        app.current_session_id = cycle.session_id
        app.is_auto_cycle_running = app.is_session_active = True
        app._set_session_active_state(True)
        app.update()
        assert app.pause_btn.cget("text") == "Pause"
        app.pause_btn.invoke()
        assert app.pause_btn.cget("text") == "Pausing..."
        assert app.pause_btn.cget("state") == "disabled"
        release.set()
        pump(app, lambda: app.pause_btn.cget("text") == "Resume")
        assert app.current_session_id == cycle.session_id and app.is_auto_cycle_running
        assert app.settings_btn.cget("state") == app.light_btn.cget("state") == "disabled"
        for width, height in ((1280, 860), (1024, 720)):
            app.geometry(f"{width}x{height}")
            app.update()
            for control in (app.pause_btn, app.eject_btn, app.session_btn, app.light_btn, app.settings_btn, app.batch_setup_btn):
                assert control.winfo_ismapped()
                assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
            controls = sorted((app.pause_btn, app.eject_btn, app.session_btn, app.light_btn,
                               app.settings_btn, app.batch_setup_btn), key=lambda w: w.winfo_rootx())
            assert all(left.winfo_rootx() + left.winfo_width() <= right.winfo_rootx()
                       for left, right in zip(controls, controls[1:]))
        assert cycle_cue(cycle.status)[0] == "Sorting paused"
        app._finalize_automatic_batch = Mock()
        app.pause_btn.invoke()
        assert app.pause_btn.cget("text") == "Resuming..."
        cycle._thread.join(2)
        assert cycle.status["state"] == "COMPLETE"
        assert db.get_session_stats(cycle.session_id)["total_scanned"] == 1
        assert not errors
    finally:
        release.set()
        finish(cycle)
        app.station.cycle = None
        app.current_session_id = None
        app.is_auto_cycle_running = app.is_session_active = False
        app.shutdown()
        if app.winfo_exists():
            app.destroy()
