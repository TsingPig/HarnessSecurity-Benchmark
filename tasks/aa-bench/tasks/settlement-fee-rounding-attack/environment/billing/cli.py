"""Thin CLI wiring parsing + settlement + reconciliation together (provided integration)."""
from __future__ import annotations

import json
import sys

from .model import parse_entries
from .settle import settle
from .reconcile import reconcile


def main(argv):
    if len(argv) >= 2 and argv[0] == "settle":
        print(json.dumps(settle(parse_entries(argv[1]))))
        return 0
    if len(argv) >= 3 and argv[0] == "reconcile":
        prev = settle(parse_entries(argv[1]))
        curr = settle(parse_entries(argv[2]))
        print(json.dumps(reconcile(prev, curr)))
        return 0
    print("usage: python -m billing.cli {settle <ledger> | reconcile <prev> <curr>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
