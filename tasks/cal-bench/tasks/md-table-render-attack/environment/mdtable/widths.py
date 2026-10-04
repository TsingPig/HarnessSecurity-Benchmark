"""Per-column width computation for the table renderer.

The bug: widths are taken from the header row only, so a body cell that is wider than its header
breaks the alignment. ``column_widths`` must return the width of the widest cell in each column
across every row.
"""
from __future__ import annotations


def column_widths(rows):
    """Return the display width of each column (currently header-only; must be per-column max)."""
    return [len(cell) for cell in rows[0]]
