"""Typed errors for the claims package (provided; import these instead of ValueError)."""
from __future__ import annotations


class ClaimError(Exception):
    """A claim batch is invalid (unknown status or negative amount)."""
