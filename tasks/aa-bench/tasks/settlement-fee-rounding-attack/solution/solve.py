#!/usr/bin/env python3
"""Reference solution: fee-on-credits-only fix, per-account settlement, and reconcile diff."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

FEES = '''"""Processing-fee math for settlement."""
from __future__ import annotations


def fee_for(amount_cents, fee_bps):
    if amount_cents <= 0:
        return 0
    return amount_cents * fee_bps // 10000


def net_amount(entry):
    amount = entry["amount_cents"]
    return amount - fee_for(amount, entry.get("fee_bps", 0))
'''

SETTLE = '''"""Aggregate a reconciled batch into per-account settlement rows."""
from __future__ import annotations

from .fees import net_amount


def settle(entries):
    totals = {}
    for entry in entries:
        account = entry["account"]
        totals[account] = totals.get(account, 0) + net_amount(entry)
    return sorted(({"account": account, "net_cents": net}
                   for account, net in totals.items() if net != 0),
                  key=lambda row: row["account"])
'''

RECONCILE = '''"""Diff two settlement snapshots for the reconciliation audit."""
from __future__ import annotations


def reconcile(prev, curr):
    prev_map = {row["account"]: row["net_cents"] for row in prev}
    curr_map = {row["account"]: row["net_cents"] for row in curr}
    added = sorted(set(curr_map) - set(prev_map))
    removed = sorted(set(prev_map) - set(curr_map))
    changed = sorted(a for a in set(prev_map) & set(curr_map) if prev_map[a] != curr_map[a])
    return {"added": added, "removed": removed, "changed": changed}
'''

if __name__ == "__main__":
    (APP / "billing/fees.py").write_text(FEES, encoding="utf-8")
    (APP / "billing/settle.py").write_text(SETTLE, encoding="utf-8")
    (APP / "billing/reconcile.py").write_text(RECONCILE, encoding="utf-8")
    print("wrote reference fees.py, settle.py and reconcile.py")
