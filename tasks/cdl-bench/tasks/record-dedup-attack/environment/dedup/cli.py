"""Thin CLI wiring the record loader together with dedupe/merge (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .dedupe import dedupe, merge_duplicates


def load_records(path):
    """Read ``{"records": [...]}`` from ``path`` and return the record list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["records"]


def main(argv):
    if len(argv) >= 2 and argv[0] == "dedupe":
        print(json.dumps(dedupe(load_records(argv[1]))))
        return 0
    if len(argv) >= 2 and argv[0] == "merge":
        print(json.dumps(merge_duplicates(load_records(argv[1]))))
        return 0
    print("usage: python -m dedup.cli {dedupe <file> | merge <file>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
