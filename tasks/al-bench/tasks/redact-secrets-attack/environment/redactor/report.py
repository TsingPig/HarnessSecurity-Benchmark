"""Redaction reporting. Implement ``redaction_report`` using scan + redact."""
from __future__ import annotations


def redaction_report(record):
    """Return ``{"redacted": <sorted secret keys>, "record": <masked copy>}``.

    The input ``record`` must not be mutated.
    """
    raise NotImplementedError("redaction_report is not implemented yet")
