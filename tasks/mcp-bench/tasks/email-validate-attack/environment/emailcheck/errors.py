"""Typed errors for the email-validation package (provided; import these)."""
from __future__ import annotations


class EmailError(Exception):
    """The input to an email-validation helper is malformed or missing."""
