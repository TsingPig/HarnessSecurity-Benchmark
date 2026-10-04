"""Cell helpers shared by the renderer (provided; do not rewrite)."""
from __future__ import annotations


def escape(cell):
    """Escape a cell for a Markdown table: a literal ``|`` becomes ``\\|``."""
    return cell.replace("|", "\\|")
