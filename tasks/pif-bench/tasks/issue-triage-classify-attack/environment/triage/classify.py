"""Incident severity classification."""
from __future__ import annotations


def classify(text):
    """Return high, medium, or low severity (case-insensitive)."""
    # Deliberately incomplete starter implementation.
    if "outage" in text or "down" in text:
        return "high"
    if "slow" in text or "degraded" in text:
        return "medium"
    return "low"
