"""Typed errors for the settlement pipeline (provided; import these instead of ValueError)."""
from __future__ import annotations


class LedgerError(Exception):
    """Base class for settlement and reconciliation errors."""


class MalformedEntryError(LedgerError):
    """A ledger entry is missing required fields or carries an invalid value."""
