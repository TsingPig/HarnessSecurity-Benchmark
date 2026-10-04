"""Typed errors for the table renderer (provided; raise these instead of ValueError)."""
from __future__ import annotations


class TableError(Exception):
    """Base class for table-rendering errors."""


class AlignError(TableError):
    """An alignment spec is unknown or does not match the number of columns."""
