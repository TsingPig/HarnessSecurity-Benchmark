"""Typed errors for the scoring package (provided)."""
from __future__ import annotations


class ScoreError(Exception):
    """Weights cannot be calibrated."""
