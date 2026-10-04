"""Typed errors for the documentation search package (provided; import these)."""
from __future__ import annotations


class SearchError(Exception):
    """Base class for documentation-search errors."""


class QueryError(SearchError):
    """The query string is malformed (for example an unterminated quoted phrase)."""
