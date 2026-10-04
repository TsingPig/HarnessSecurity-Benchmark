"""Thin CLI exercising join, resolution and the containment policy (provided integration)."""
from __future__ import annotations

import sys

from .join import safe_join
from .resolve import resolve_within
from .policy import is_allowed
from .errors import PathError


def main(argv):
    if len(argv) >= 3 and argv[0] == "join":
        result = safe_join(argv[1], argv[2])
        print("REJECT" if result is None else result)
        return 1 if result is None else 0
    if len(argv) >= 3 and argv[0] == "resolve":
        try:
            print(resolve_within(argv[1], argv[2:]))
        except PathError as error:
            print(f"REJECT: {error}", file=sys.stderr)
            return 1
        return 0
    if len(argv) >= 3 and argv[0] == "allowed":
        print("yes" if is_allowed(argv[1], argv[2]) else "no")
        return 0
    print("usage: python -m pathsafe.cli {join <base> <rel> | resolve <base> <part...> | "
          "allowed <base> <path>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
