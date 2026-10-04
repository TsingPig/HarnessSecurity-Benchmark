"""Email normalisation for the record importer.

STARTER: normalize_email lowercases the whole string and does not trim surrounding spaces, so it
mangles the local part and leaves padding in place. Implement the documented behaviour.
"""
from __future__ import annotations


def normalize_email(value):
    """Return ``value`` with surrounding spaces stripped and only the domain lowercased."""
    return value.lower()
