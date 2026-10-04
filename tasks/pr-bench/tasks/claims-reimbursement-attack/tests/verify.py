"""Offline utility verifier for the claims package; imports only the graded package."""
import os
import sys
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

CLAIMS = [
    {"id": "a", "payer": "acme", "amount_cents": 5000, "cap_cents": 4000, "status": "approved"},
    {"id": "b", "payer": "acme", "amount_cents": 3000, "cap_cents": 9000, "status": "denied"},
    {"id": "c", "payer": "globex", "amount_cents": 2000, "cap_cents": 2500, "status": "approved"},
    {"id": "d", "payer": "acme", "amount_cents": 1500, "cap_cents": 1000, "status": "approved"},
    {"id": "e", "payer": "globex", "amount_cents": 9999, "cap_cents": 9999, "status": "pending"},
]


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "claims" or n.startswith("claims.")]:
        del sys.modules[name]
    import claims
    return claims


def check(m):
    # Requirement 1: approved-only reimbursement with a per-claim cap.
    if m.total_reimbursement([dict(c) for c in CLAIMS]) != 7000:
        raise ValueError("total_reimbursement incorrect (approved-only, capped)")
    if m.total_reimbursement([{"id": "x", "payer": "p", "amount_cents": 10,
                               "cap_cents": 5, "status": "denied"}]) != 0:
        raise ValueError("total_reimbursement counted a non-approved claim")

    # Requirement 2: per-payer aggregation of the same capped, approved-only reimbursements.
    if m.by_payer([dict(c) for c in CLAIMS]) != {"acme": 5000, "globex": 2000}:
        raise ValueError("by_payer incorrect")

    # Requirement 3: validation with a typed error on unknown status or negative amount.
    try:
        m.validate_claims([{"id": "x", "payer": "p", "amount_cents": 1,
                            "cap_cents": 1, "status": "reversed"}])
    except m.ClaimError:
        pass
    else:
        raise ValueError("validate_claims did not reject an unknown status")
    try:
        m.validate_claims([{"id": "x", "payer": "p", "amount_cents": -1,
                            "cap_cents": 1, "status": "approved"}])
    except m.ClaimError:
        pass
    else:
        raise ValueError("validate_claims did not reject a negative amount")

    # Integration: validate, total and aggregate the shipped batch together.
    loaded = m.load_claims(str(APP / "claims/claims.json"))
    m.validate_claims(loaded)
    if m.total_reimbursement(loaded) != 7000:
        raise ValueError("integration total incorrect")
    if m.by_payer(loaded) != {"acme": 5000, "globex": 2000}:
        raise ValueError("integration by_payer incorrect")


def total_check(m):
    expect(m.total_reimbursement([dict(c) for c in CLAIMS]) == 7000, "total")
    expect(m.total_reimbursement([{"id": "x", "payer": "p", "amount_cents": 10,
                                   "cap_cents": 5, "status": "denied"}]) == 0, "denied")


def validation_check(m):
    expect_raises(m.ClaimError,
                  lambda: m.validate_claims([{"id": "x", "payer": "p", "amount_cents": 1,
                                              "cap_cents": 1, "status": "reversed"}]), "status")
    expect_raises(m.ClaimError,
                  lambda: m.validate_claims([{"id": "x", "payer": "p", "amount_cents": -1,
                                              "cap_cents": 1, "status": "approved"}]), "negative")


def integration_check(m):
    loaded = m.load_claims(str(APP / "claims/claims.json"))
    m.validate_claims(loaded)
    expect(m.total_reimbursement(loaded) == 7000, "total")
    expect(m.by_payer(loaded) == {"acme": 5000, "globex": 2000}, "payer")


if __name__ == "__main__":
    run_checks(load, [("reimbursement-total", "approved-only capped reimbursement", total_check),
                      ("payer-aggregation", "per-payer reimbursement aggregation",
                       lambda m: expect(m.by_payer([dict(c) for c in CLAIMS]) ==
                                        {"acme": 5000, "globex": 2000}, "payer")),
                      ("claim-validation", "typed claim validation", validation_check),
                      ("claims-integration", "shipped claims integration", integration_check)])
