"""Typed errors for the retry scheduler (provided; import these instead of bare ValueError).

``InvalidAttemptError`` also subclasses ``ValueError`` so existing ``except ValueError`` callers
keep working.
"""
from __future__ import annotations


class SchedulerError(Exception):
    """Base class for scheduler errors."""


class InvalidAttemptError(SchedulerError, ValueError):
    """A retry attempt index or schedule length is negative."""
