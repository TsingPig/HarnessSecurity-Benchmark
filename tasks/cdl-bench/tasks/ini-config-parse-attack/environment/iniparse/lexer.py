"""Low-level line helpers for the INI parser (provided; do not rewrite)."""
from __future__ import annotations


def logical_lines(text):
    """Yield ``(lineno, line)`` for each meaningful line in ``text``.

    Blank lines and lines whose first non-space character is ``#`` are skipped. The yielded
    line is stripped of surrounding whitespace but keeps its inner spacing.
    """
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        yield lineno, stripped
