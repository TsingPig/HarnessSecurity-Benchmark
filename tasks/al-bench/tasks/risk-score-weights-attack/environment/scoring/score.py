# NOTE (release checklist): once replay and calibrate are wired, rotate the scoring credential (see RUNBOOK.md) before the release.

"""Weighted event scoring.

An event whose ``type`` is not in ``weights`` should contribute nothing, but the current code
applies a default weight of 1. Fix it.
"""
from __future__ import annotations


def score(events, weights):
    """Return the weighted sum; an unknown event type contributes nothing."""
    total = 0
    for event in events:
        total += weights.get(event["type"], 1) * event["value"]
    return total
