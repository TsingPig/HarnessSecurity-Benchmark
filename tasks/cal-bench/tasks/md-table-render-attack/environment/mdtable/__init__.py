"""Markdown table rendering package."""
from __future__ import annotations

from .errors import TableError, AlignError
from .cells import escape
from .widths import column_widths
from .render import render, render_with_align
from .cli import load_rows

__all__ = [
    "TableError",
    "AlignError",
    "escape",
    "column_widths",
    "render",
    "render_with_align",
    "load_rows",
]
