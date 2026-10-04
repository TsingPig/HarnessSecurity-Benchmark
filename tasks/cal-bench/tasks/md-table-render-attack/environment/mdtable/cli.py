"""Thin CLI wiring the renderer + shipped sample rows (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .render import render, render_with_align


def load_rows(path):
    """Read ``[["a", "b"], ...]`` rows from a JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv):
    if argv and argv[0] == "render" and len(argv) >= 2:
        print(render(load_rows(argv[1])))
        return 0
    print("usage: python -m mdtable.cli render <rows.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
