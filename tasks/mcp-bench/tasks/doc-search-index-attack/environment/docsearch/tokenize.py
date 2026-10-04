"""Tokenizer shared by the index and query layers (provided; do not rewrite)."""
from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text):
    """Return the lowercased alphanumeric word tokens of ``text`` in order."""
    return _WORD.findall(text.lower())
