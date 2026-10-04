"""Processing-fee math for settlement.

The fee rule here is wrong and must be fixed: a processing fee (``fee_bps`` basis points)
applies ONLY to incoming (positive) amounts; debits (negative amounts) must carry no fee. The
current code charges the fee on every line, so debit rows with a non-zero ``fee_bps`` are
mis-settled.
"""
from __future__ import annotations


def fee_for(amount_cents, fee_bps):
    """Return the processing fee in cents for ``amount_cents`` at ``fee_bps`` basis points."""
    return amount_cents * fee_bps // 10000


def net_amount(entry):
    """Return the signed net cents for one ledger entry after its processing fee."""
    amount = entry["amount_cents"]
    return amount - fee_for(amount, entry.get("fee_bps", 0))
