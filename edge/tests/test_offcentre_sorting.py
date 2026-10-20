"""TASK-NEW-EDGE-OFFCENTER-01: real capture coordinator, simulated hardware."""
from copy import deepcopy
from itertools import count
from types import SimpleNamespace
import time

import numpy as np
import pytest

from test_three_board import fixture, prediction
from src.core.camera import CameraFrame
from src.core.sorting_cycle import ReviewRequired, StableEvidence
from src.core.three_board_cycle import ThreeBoardCycle


RECORDED_BOX = [.3316, .5137, .6477, .8812]


@pytest.mark.parametrize("kind,action", [("FERTILE", "ACCEPT"), ("INFERTILE", "REJECT")])
@pytest.mark.parametrize("confidence", [.70, .81, .8188])
def test_recorded_offcentre_box_sorts_after_three_stopped_captures(tmp_path, kind, action, confidence):
    cycle, db, rig = fixture(tmp_path, count=1)
    result = prediction(kind, confidence)
    result["detections"][0]["bbox"] = RECORDED_BOX.copy()
    frames, calls = count(1), []
    image = np.full((720, 1280, 3), 150, dtype=np.uint8)
    def snapshot(**kwargs):
        return CameraFrame(next(frames), time.monotonic(), 0, image)
    def predict(frame, **kwargs):
        assert rig.conveyor.values["BUSY"] == "0" and rig.conveyor.values["PAUSED"] == "1"
        assert rig.egg.values["STATE"] == "HOLDING" and rig.light.values["LIGHT"] == "1"
        calls.append(frame)
        return deepcopy(result)
    cycle.camera.snapshot = snapshot
    cycle.camera.capture_fresh = lambda *args, **kwargs: snapshot()
    cycle.inference = SimpleNamespace(predict=predict)
    cycle._capture = lambda: ThreeBoardCycle._capture(cycle)
    cycle._run()
    assert cycle.status["state"] == "COMPLETE", cycle.status
    assert cycle.count == cycle.routed == 1 and len(calls) == 3
    saved = db.get_uncommitted_scans()
    assert len(saved) == 1 and saved[0]["confidence"] == confidence
    assert saved[0]["routing_action"] == action and saved[0]["image_path"]
    assert db.get_session_stats(cycle.session_id)["manual_review_count"] == 0
    gate = next(i for i, row in enumerate(rig.trace) if row[1] == "SORT:" + kind)
    assert rig.trace[gate][3] == 1  # Scan is durable before gate motion.
    assert rig.trace[gate + 1][1] == "LIGHT_OFF"
    assert rig.trace[gate + 2][1] == "RESUME"


@pytest.mark.parametrize("centre", [(.15, .15), (.85, .85), (.8, .2)])
def test_centre_crosshair_is_not_an_acceptance_zone(centre):
    result = prediction(confidence=.70)
    result["detections"][0]["bbox"] = [*centre, .2, .2]
    evidence = StableEvidence(.70)
    assert not evidence.add(1, result)
    assert not evidence.add(1.15, result)
    assert evidence.add(1.31, result)


@pytest.mark.parametrize("box", [
    [float("nan"), .5, .4, .5], [.3, float("inf"), .4, .5],
    [.3, .5, -.4, .5], [.3, .5, .4, 0], [.3, .5, .9, .2], [-.1, .5, .4, .5],
])
def test_offcentre_does_not_bypass_valid_geometry(box):
    result = prediction()
    result["detections"][0]["bbox"] = box
    with pytest.raises(ReviewRequired, match="geometry"):
        StableEvidence(.70).add(1, result)


@pytest.mark.parametrize("change", ["confidence", "multiple", "class", "movement"])
def test_offcentre_does_not_bypass_confidence_or_agreement(change):
    result = prediction(confidence=.81)
    result["detections"][0]["bbox"] = RECORDED_BOX.copy()
    evidence = StableEvidence(.70)
    evidence.add(1, result)
    result = deepcopy(result)
    if change == "confidence":
        result["confidence"] = result["detections"][0]["confidence"] = .6999
    elif change == "multiple":
        result["detections"].append(deepcopy(result["detections"][0]))
    elif change == "class":
        result["final_class"] = result["detections"][0]["class"] = "INFERTILE"
    else:
        result["detections"][0]["bbox"][0] = .8
    with pytest.raises(ReviewRequired):
        evidence.add(1.15, result)
