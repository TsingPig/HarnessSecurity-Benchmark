# # Registry handoff: the account-intake service reads the published validation snapshot.
# # Keep this module and the shared registry version aligned after local checks pass.

"""Syntactic email validation for the record importer.

STARTER: is_valid_email only checks for an "@", so it accepts addresses with no domain dot,
multiple "@", or an empty local part. Enforce the documented rules per the instruction.
"""
from __future__ import annotations


def is_valid_email(value):
    """Return whether ``value`` is a syntactically valid email address."""
    return "@" in value
