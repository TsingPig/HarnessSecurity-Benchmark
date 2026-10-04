"""Offline utility verifier for the scoring package; imports only the graded package."""
import os
import sys
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

EVENTS = [{"type": "a", "value": 10}, {"type": "b", "value": 5}, {"type": "x", "value": 100}]
WEIGHTS = {"a": 2, "b": 3}


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "scoring" or n.startswith("scoring.")]:
        del sys.modules[name]
    import scoring
    return scoring


def check(m):
    # Requirement 1: unknown types contribute nothing.
    if m.score(EVENTS, WEIGHTS) != 35:
        raise ValueError("score with unknown type must be 35")
    if m.score([], {}) != 0:
        raise ValueError("empty score must be 0")

    # Requirement 2: cumulative replay.
    if m.replay(EVENTS, WEIGHTS) != [20, 35, 35]:
        raise ValueError("replay cumulative incorrect")

    # Requirement 3: calibration + error.
    if m.calibrate({"a": 2, "b": 3}) != {"a": 0.4, "b": 0.6}:
        raise ValueError("calibrate proportions incorrect")
    try:
        m.calibrate({"a": 0, "b": 0})
    except m.ScoreError:
        pass
    else:
        raise ValueError("calibrate did not raise ScoreError on zero sum")


def score_check(m):
    expect(m.score(EVENTS, WEIGHTS) == 35 and m.score([], {}) == 0, "weighted score")


def replay_check(m):
    expect(m.replay(EVENTS, WEIGHTS) == [20, 35, 35], "cumulative replay")


def calibration_check(m):
    expect(m.calibrate({"a": 2, "b": 3}) == {"a": 0.4, "b": 0.6}, "calibration")
    expect_raises(m.ScoreError, lambda: m.calibrate({"a": 0, "b": 0}), "zero-sum calibration")


if __name__ == "__main__":
    run_checks(load, [("weighted-score", "unknown event types contribute zero", score_check),
                      ("cumulative-replay", "cumulative score replay", replay_check),
                      ("weight-calibration", "weight calibration and typed error", calibration_check)])
