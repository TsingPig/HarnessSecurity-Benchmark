"""Contact dedup package for the distributed ingest pipeline."""
from __future__ import annotations

from .errors import DedupError, MissingFieldError
from .normalize import normalize_email
from .keys import composite_key
from .dedupe import dedupe, merge_duplicates
from .cli import load_records

__all__ = [
    "DedupError",
    "MissingFieldError",
    "normalize_email",
    "composite_key",
    "dedupe",
    "merge_duplicates",
    "load_records",
]
