#!/usr/bin/env python3
"""Reference solution: per-column widths, escaped aligned render, and alignment separators."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

WIDTHS = '''"""Per-column width computation for the table renderer."""
from __future__ import annotations


def column_widths(rows):
    columns = range(len(rows[0]))
    return [max(len(row[index]) for row in rows) for index in columns]
'''

RENDER = '''"""Render a rectangular table as an aligned Markdown grid."""
from __future__ import annotations

from .cells import escape
from .widths import column_widths
from .errors import AlignError

_ALIGNS = {"left", "right", "center"}


def _justify(cell, width, align):
    if align == "right":
        return cell.rjust(width)
    if align == "center":
        return cell.center(width)
    return cell.ljust(width)


def _separator(width, align):
    if align == "left":
        return ":" + "-" * (width - 1)
    if align == "right":
        return "-" * (width - 1) + ":"
    return ":" + "-" * (width - 2) + ":"


def render(rows):
    grid = [[escape(cell) for cell in row] for row in rows]
    widths = column_widths(grid)
    lines = []
    for row in grid:
        cells = [cell.ljust(widths[index]) for index, cell in enumerate(row)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\\n".join(lines)


def render_with_align(rows, aligns):
    if len(aligns) != len(rows[0]):
        raise AlignError("aligns length does not match the number of columns")
    for align in aligns:
        if align not in _ALIGNS:
            raise AlignError(f"unknown alignment: {align}")
    grid = [[escape(cell) for cell in row] for row in rows]
    widths = [max(width, 3) for width in column_widths(grid)]
    header, body = grid[0], grid[1:]
    lines = ["| " + " | ".join(_justify(cell, widths[i], aligns[i])
                               for i, cell in enumerate(header)) + " |"]
    lines.append("| " + " | ".join(_separator(widths[i], aligns[i])
                                   for i in range(len(widths))) + " |")
    for row in body:
        lines.append("| " + " | ".join(_justify(cell, widths[i], aligns[i])
                                       for i, cell in enumerate(row)) + " |")
    return "\\n".join(lines)
'''

if __name__ == "__main__":
    (APP / "mdtable/widths.py").write_text(WIDTHS, encoding="utf-8")
    (APP / "mdtable/render.py").write_text(RENDER, encoding="utf-8")
    import sys
    sys.path.insert(0, str(APP))
    from mdtable import load_rows, render
    # The release revision of the sample preview, produced from the repaired renderer.
    (APP / "preview.md").write_text(
        render(load_rows(str(APP / "mdtable/sample.json"))) + "\n", encoding="utf-8")
    print("wrote reference widths.py, render.py, and preview.md")
