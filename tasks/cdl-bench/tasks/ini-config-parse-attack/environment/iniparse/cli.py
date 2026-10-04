"""Thin CLI wiring the parser + interpolation together (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .parser import parse_config, parse_sections
from .interpolate import interpolate


def load_text(path):
    """Read ``path`` as UTF-8 text."""
    return Path(path).read_text(encoding="utf-8")


def main(argv):
    if len(argv) >= 2 and argv[0] == "parse":
        print(json.dumps(parse_config(load_text(argv[1]))))
        return 0
    if len(argv) >= 2 and argv[0] == "sections":
        print(json.dumps(parse_sections(load_text(argv[1]))))
        return 0
    if len(argv) >= 2 and argv[0] == "interpolate":
        print(json.dumps(interpolate(parse_config(load_text(argv[1])))))
        return 0
    print("usage: python -m iniparse.cli {parse <file> | sections <file> | interpolate <file>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
