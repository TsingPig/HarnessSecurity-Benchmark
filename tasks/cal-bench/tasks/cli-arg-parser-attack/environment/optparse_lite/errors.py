"""Typed errors for the option parser (provided; raise these instead of ValueError)."""
from __future__ import annotations


class ParserError(Exception):
    """Base class for option-parsing errors."""


class OptionError(ParserError):
    """A long option is not declared in the typed schema, or its value cannot be coerced."""
