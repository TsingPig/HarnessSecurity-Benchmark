"""Dedup key helpers (provided; do not rewrite)."""
from __future__ import annotations

from .errors import MissingFieldError
from .normalize import normalize_email


def composite_key(record):
    """Return the canonical dedup key for ``record`` (its normalized ``email``).

    Raise ``MissingFieldError`` when the record has no ``email`` field.
    """
    if "email" not in record:
        raise MissingFieldError("record has no 'email' field")
    return normalize_email(record["email"])
