"""Deterministic, bounded backoff jitter (provided; do not rewrite).

Jitter is disabled by default (``jitter_ms=0``) so the base schedule is exact; when enabled it
adds a deterministic offset derived from the attempt so retries stay reproducible.
"""
from __future__ import annotations

import hashlib


def apply_jitter(delay_ms, attempt, jitter_ms=0):
    """Return ``delay_ms`` plus a deterministic offset in ``[0, jitter_ms]`` (0 by default)."""
    if jitter_ms <= 0:
        return delay_ms
    digest = hashlib.sha256(f"{attempt}:{delay_ms}".encode("utf-8")).hexdigest()
    return delay_ms + int(digest, 16) % (jitter_ms + 1)
