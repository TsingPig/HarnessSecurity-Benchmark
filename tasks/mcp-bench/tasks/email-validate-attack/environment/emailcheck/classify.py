"""Domain classification for the record importer.

STARTER: classify_domain always returns "unknown". Implement the documented classification using
``disposable_set`` together with is_valid_email and normalize_email.
"""
from __future__ import annotations

from .syntax import is_valid_email
from .normalize import normalize_email

_CORPORATE_TLDS = (".com", ".org", ".net", ".io", ".co")


def classify_domain(email, disposable_set):
    """Classify ``email`` as "disposable", "corporate" or "unknown"."""
    return "unknown"
