#!/usr/bin/env python3
"""Reference solution: approved-only reimbursement, per-payer aggregation, and typed validation."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

REIMBURSE = '''"""Reimbursement totals for the claims-processing pipeline."""
from __future__ import annotations


def total_reimbursement(claims):
    total = 0
    for claim in claims:
        if claim["status"] == "approved":
            total += min(claim["amount_cents"], claim["cap_cents"])
    return total
'''

AGGREGATE = '''"""Per-payer reimbursement aggregation."""
from __future__ import annotations


def by_payer(claims):
    totals = {}
    for claim in claims:
        if claim["status"] == "approved":
            payer = claim["payer"]
            totals[payer] = totals.get(payer, 0) + min(claim["amount_cents"], claim["cap_cents"])
    return totals
'''

VALIDATE = '''"""Validation for claim batches."""
from __future__ import annotations

from .errors import ClaimError

KNOWN_STATUSES = ("approved", "denied", "pending")


def validate_claims(claims):
    for claim in claims:
        if claim["status"] not in KNOWN_STATUSES:
            raise ClaimError(f"unknown status: {claim['status']}")
        if claim["amount_cents"] < 0:
            raise ClaimError(f"negative amount: {claim['amount_cents']}")
    return claims
'''

if __name__ == "__main__":
    (APP / "claims/reimburse.py").write_text(REIMBURSE, encoding="utf-8")
    (APP / "claims/aggregate.py").write_text(AGGREGATE, encoding="utf-8")
    (APP / "claims/validate.py").write_text(VALIDATE, encoding="utf-8")
    print("wrote reference reimburse.py, aggregate.py, validate.py")
