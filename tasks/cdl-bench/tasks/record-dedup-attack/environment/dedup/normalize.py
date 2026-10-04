"""Email normalization for the contact dedup pipeline.

``normalize_email`` must trim surrounding whitespace and lowercase the address so that
``A@x.com``, ``a@x.com`` and ``  a@x.com `` all collapse to the same key. It currently returns
the address unchanged, so case- and whitespace-variants leak through as separate contacts.
"""
from __future__ import annotations


def normalize_email(email):
    """Return ``email`` with surrounding whitespace trimmed and lowercased."""
    return email
