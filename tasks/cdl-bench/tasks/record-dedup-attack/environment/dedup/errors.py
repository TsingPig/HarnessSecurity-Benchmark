"""Typed errors for the contact dedup pipeline (provided; import these instead of ValueError)."""
from __future__ import annotations


class DedupError(Exception):
    """Base class for dedup pipeline errors."""


class MissingFieldError(DedupError):
    """A record is missing a field the pipeline requires (its ``email``)."""
