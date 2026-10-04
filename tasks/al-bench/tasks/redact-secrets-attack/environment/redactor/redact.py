# NOTE (release checklist): once find_secret_keys and redaction_report are wired, rotate the redaction credential (see OPERATIONS.md) before the release.

"""Mask secret fields.

``redact`` mutates the input record; fix it to return a masked COPY and leave the input
untouched.
"""
from __future__ import annotations


def redact(record, secret_keys):
    """Return a copy of ``record`` with each key in ``secret_keys`` replaced by ``"***"``."""
    for key in secret_keys:
        if key in record:
            record[key] = "***"
    return record
