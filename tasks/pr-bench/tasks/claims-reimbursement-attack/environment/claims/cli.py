"""Thin CLI wiring the loader, validation, reimbursement and aggregation (provided integration)."""
from __future__ import annotations

import json
import sys

from .model import load_claims
from .reimburse import total_reimbursement
from .aggregate import by_payer
from .validate import validate_claims


def main(argv):
    if len(argv) >= 2 and argv[0] == "total":
        claims = load_claims(argv[1])
        validate_claims(claims)
        print(json.dumps({"total": total_reimbursement(claims)}))
        return 0
    if len(argv) >= 2 and argv[0] == "by-payer":
        claims = load_claims(argv[1])
        validate_claims(claims)
        print(json.dumps({"by_payer": by_payer(claims)}))
        return 0
    print("usage: python -m claims.cli {total <file> | by-payer <file>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
