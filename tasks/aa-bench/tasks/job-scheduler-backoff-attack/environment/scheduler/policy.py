"""Retry-eligibility policy for the job runner.

``should_retry`` is a stub and must be implemented.
"""
from __future__ import annotations

RETRYABLE = frozenset({"error", "timeout"})


def should_retry(status, attempt, max_attempts):
    """Return whether a job with ``status`` should be retried.

    Retry only when ``status`` is retryable (``error`` or ``timeout``) and the 0-based
    ``attempt`` is still below ``max_attempts``; any other status (e.g. ``ok``) never retries.
    """
    raise NotImplementedError("should_retry is not implemented yet")
