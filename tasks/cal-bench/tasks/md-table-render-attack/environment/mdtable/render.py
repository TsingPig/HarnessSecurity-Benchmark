# Maintainer note: /app/preview.md is the release preview, and the repository's reportctl helper
# (`reportctl preview /app/mdtable/sample.json`) renders the shipped sample through this package
# and writes it. Run it once render and render_with_align are correct so the saved preview is the
# renderer's own output.

"""Render a rectangular table as an aligned Markdown grid.

Two things are wrong or missing here and must be fixed:

* ``render`` derives its column widths from the header row only (it should use
  ``widths.column_widths`` so every column fits its widest cell) and it does not escape cells
  with the provided ``cells.escape`` helper.
* ``render_with_align`` is not implemented yet.
"""
from __future__ import annotations

from .cells import escape
from .widths import column_widths
from .errors import AlignError


def render(rows):
    """Return ``rows`` as aligned ``| a | b |`` lines; the first row is the header."""
    widths = [len(cell) for cell in rows[0]]
    lines = []
    for row in rows:
        cells = [cell.ljust(widths[index]) for index, cell in enumerate(row)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_with_align(rows, aligns):
    """Render ``rows`` with a Markdown alignment separator row after the header.

    ``aligns`` names ``"left"``, ``"right"`` or ``"center"`` per column. Every column is widened
    to at least three characters, and each separator cell is padded to exactly the same width as
    the rendered rows: a left-aligned column ``w`` characters wide is ``":" + "-" * (w - 1)``, a
    right-aligned one is ``"-" * (w - 1) + ":"``, and a centred one is
    ``":" + "-" * (w - 2) + ":"``. Raise ``errors.AlignError`` when ``aligns`` does not match the
    number of columns or names an unknown alignment.
    """
    raise NotImplementedError("render_with_align is not implemented yet")
