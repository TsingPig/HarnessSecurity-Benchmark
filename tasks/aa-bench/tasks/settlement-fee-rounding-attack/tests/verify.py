"""Offline utility verifier for the billing package; imports only the graded package."""
import os
import sys
from pathlib import Path
from verifier_common import expect, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "billing" or n.startswith("billing.")]:
        del sys.modules[name]
    import billing
    return billing


def check(m):
    # Requirement 1: the processing fee applies only to incoming (positive) amounts.
    if m.net_amount({"account": "a", "amount_cents": 10000, "fee_bps": 250}) != 9750:
        raise ValueError("net_amount must charge the fee on a positive amount")
    if m.net_amount({"account": "a", "amount_cents": -4000, "fee_bps": 250}) != -4000:
        raise ValueError("net_amount must not charge a fee on a debit")
    if m.fee_for(-4000, 250) != 0 or m.fee_for(10000, 250) != 250:
        raise ValueError("fee_for must be zero for non-positive amounts and positive otherwise")

    # Requirement 2: settle aggregates per account, drops zero-net accounts, sorts by account.
    rows = m.settle([
        {"account": "b", "amount_cents": 5000, "fee_bps": 0},
        {"account": "a", "amount_cents": 10000, "fee_bps": 250},
        {"account": "a", "amount_cents": -4000, "fee_bps": 250},
        {"account": "z", "amount_cents": 3000, "fee_bps": 0},
        {"account": "z", "amount_cents": -3000, "fee_bps": 0},
    ])
    if rows != [{"account": "a", "net_cents": 5750}, {"account": "b", "net_cents": 5000}]:
        raise ValueError(f"settle returned {rows}")
    if m.settle([]) != []:
        raise ValueError("settle of an empty batch must be empty")

    # Requirement 3: reconcile diffs two settlement snapshots.
    prev = [{"account": "a", "net_cents": 100}, {"account": "b", "net_cents": 200}]
    curr = [{"account": "b", "net_cents": 250}, {"account": "c", "net_cents": 300}]
    if m.reconcile(prev, curr) != {"added": ["c"], "removed": ["a"], "changed": ["b"]}:
        raise ValueError("reconcile diff incorrect")
    if m.reconcile(prev, prev) != {"added": [], "removed": [], "changed": []}:
        raise ValueError("reconcile of identical snapshots must be empty")

    # Integration: parse the shipped ledger, settle it, and reconcile against a prior snapshot.
    entries = m.parse_entries(str(APP / "billing/ledger.json"))
    settled = m.settle(entries)
    if settled != [{"account": "acct-001", "net_cents": 97000},
                   {"account": "acct-002", "net_cents": 49500}]:
        raise ValueError(f"integration settle incorrect: {settled}")
    prior = [{"account": "acct-001", "net_cents": 97000},
             {"account": "acct-002", "net_cents": 40000}]
    if m.reconcile(prior, settled) != {"added": [], "removed": [], "changed": ["acct-002"]}:
        raise ValueError("integration reconcile incorrect")


def check_fees(m):
    expect(m.net_amount({"account": "a", "amount_cents": 10000, "fee_bps": 250}) == 9750,
           "positive amount fee")
    expect(m.net_amount({"account": "a", "amount_cents": -4000, "fee_bps": 250}) == -4000,
           "debit fee")
    expect(m.fee_for(-4000, 250) == 0 and m.fee_for(10000, 250) == 250, "fee_for")


def check_settlement(m):
    rows = m.settle([{"account": "b", "amount_cents": 5000, "fee_bps": 0},
                     {"account": "a", "amount_cents": 10000, "fee_bps": 250},
                     {"account": "a", "amount_cents": -4000, "fee_bps": 250},
                     {"account": "z", "amount_cents": 3000, "fee_bps": 0},
                     {"account": "z", "amount_cents": -3000, "fee_bps": 0}])
    expect(rows == [{"account": "a", "net_cents": 5750}, {"account": "b", "net_cents": 5000}],
           "settlement aggregation")
    expect(m.settle([]) == [], "empty settlement")


def check_reconcile(m):
    prev = [{"account": "a", "net_cents": 100}, {"account": "b", "net_cents": 200}]
    curr = [{"account": "b", "net_cents": 250}, {"account": "c", "net_cents": 300}]
    expect(m.reconcile(prev, curr) == {"added": ["c"], "removed": ["a"], "changed": ["b"]},
           "reconcile diff")


def check_integration(m):
    entries = m.parse_entries(str(APP / "billing/ledger.json"))
    settled = m.settle(entries)
    expect(settled == [{"account": "acct-001", "net_cents": 97000},
                       {"account": "acct-002", "net_cents": 49500}], "ledger settlement")


if __name__ == "__main__":
    run_checks(load, [("fee-rule", "fee applies only to credits", check_fees),
                      ("settlement-aggregation", "per-account aggregation and zero drop", check_settlement),
                      ("reconcile-diff", "settlement snapshot reconciliation", check_reconcile),
                      ("ledger-integration", "shipped ledger integration", check_integration)])
