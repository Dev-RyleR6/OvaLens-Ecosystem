"""TASK-NEW-EDGE-CONFIDENCE-70-01: stopped evidence and durable 70% routing."""
import uuid

import pytest

from test_three_board import fixture, prediction
from src.core.settings import EdgeSettings, SettingsStore
from src.core.sorting_cycle import ReviewRequired, StableEvidence


def test_seventy_percent_defaults_and_saved_custom_threshold(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.load().detection.sort_confidence == .70
    settings = EdgeSettings.three_board()
    assert settings.detection.sort_confidence == .70
    for threshold in (.70, .85):
        settings.detection.sort_confidence = threshold
        store.save(settings)
        assert store.load().detection.sort_confidence == threshold
    settings.detection.sort_confidence = .6999
    with pytest.raises(ValueError, match="sort_confidence"):
        settings.validate()


@pytest.mark.parametrize("kind,angle,action", [("FERTILE", "180", "ACCEPT"), ("INFERTILE", "120", "REJECT")])
@pytest.mark.parametrize("confidence", [.70, .72, .7499])
def test_seventy_percent_stable_decision_saves_before_gate_release(tmp_path, kind, angle, action, confidence):
    cycle, db, rig = fixture(tmp_path, count=1)
    def capture():
        evidence = StableEvidence(cycle.settings.detection.sort_confidence)
        result = prediction(kind, confidence)
        assert not evidence.add(1, result)
        assert not evidence.add(1.15, result)
        assert evidence.add(1.31, result)
        return evidence.result(), {"frames": 3, "span_ms": 310}
    cycle._capture = capture
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    saved = db.get_uncommitted_scans()
    assert len(saved) == 1 and saved[0]["confidence"] == confidence
    assert saved[0]["routing_action"] == action
    assert db.get_session_stats(cycle.session_id)["manual_review_count"] == 0
    index = next(i for i, row in enumerate(rig.trace) if row[1] == "SORT:" + kind)
    assert rig.trace[index][3] == 1  # Already committed before the servo command.
    assert rig.trace[index + 1][1] == "LIGHT_OFF"
    assert rig.trace[index + 2][1] == "RESUME"
    assert angle == str(cycle.settings.calibration.fertile_angle if kind == "FERTILE"
                        else cycle.settings.calibration.infertile_angle)


@pytest.mark.parametrize("threshold,confidence", [(.70, .6999), (.85, .80)])
def test_below_configured_threshold_still_requires_review(threshold, confidence):
    evidence = StableEvidence(threshold)
    with pytest.raises(ReviewRequired, match="confidence"):
        evidence.add(1, prediction(confidence=confidence))


def test_storage_never_auto_routes_below_seventy_percent(tmp_path):
    cycle, db, _ = fixture(tmp_path, count=1)
    db.create_session(cycle.session_id, cycle.batch_id, cycle.device_id, "DAY_10", "operator")
    scan_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="MANUAL_REVIEW"):
        db.record_scan(scan_id, cycle.session_id, cycle.batch_id, 1, "FERTILE", .6999, 8, "ACCEPT", [])
    assert not db.get_uncommitted_scans()
    db.record_scan(scan_id, cycle.session_id, cycle.batch_id, 1, "FERTILE", .6999, 8, "MANUAL_REVIEW", [])
    assert db.get_session_stats(cycle.session_id)["manual_review_count"] == 1
