"""Query-string parsing for the documentation search package.

STARTER: this splits on whitespace only, so it breaks up ``"quoted phrases"`` and never reports
an unterminated quote. Implement ``parse_query`` per the instruction.
"""
from __future__ import annotations

from .errors import QueryError


def parse_query(query):
    """Split ``query`` into search terms, honouring double-quoted phrases."""
    return query.split()
