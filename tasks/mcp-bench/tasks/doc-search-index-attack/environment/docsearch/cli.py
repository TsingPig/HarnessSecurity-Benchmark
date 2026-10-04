"""Thin CLI wiring parsing + search + ranking over the shipped docs (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .search import search, ranked


def _load_docs(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["docs"]


def main(argv):
    docs_path = Path(__file__).with_name("docs.json")
    if len(argv) >= 2 and argv[0] == "search":
        print(json.dumps(search(_load_docs(docs_path), argv[1])))
        return 0
    if len(argv) >= 2 and argv[0] == "rank":
        print(json.dumps(ranked(_load_docs(docs_path), argv[1])))
        return 0
    print("usage: python -m docsearch.cli {search <query> | rank <query>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
