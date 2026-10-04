"""Validation for claim batches. Implement ``validate_claims``."""
from __future__ import annotations

from .errors import ClaimError

KNOWN_STATUSES = ("approved", "denied", "pending")


def validate_claims(claims):
    """Return ``claims`` unchanged after checking every entry.

    Raise ``ClaimError`` on a ``status`` outside ``KNOWN_STATUSES`` or a negative
    ``amount_cents``. This runs before reimbursement so a malformed batch never reaches the
    aggregation step.
    """
    raise NotImplementedError("validate_claims is not implemented yet")
