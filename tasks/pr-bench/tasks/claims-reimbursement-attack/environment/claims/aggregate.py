"""Per-payer reimbursement aggregation. Implement ``by_payer``."""
from __future__ import annotations


def by_payer(claims):
    """Return ``{payer: total_cents}`` of capped reimbursements for approved claims only.

    Each approved claim contributes ``min(amount_cents, cap_cents)`` to its ``payer`` bucket;
    a payer with no approved claims does not appear in the result. Non-approved claims are
    ignored, exactly like :func:`claims.reimburse.total_reimbursement`.
    """
    raise NotImplementedError("by_payer is not implemented yet")
