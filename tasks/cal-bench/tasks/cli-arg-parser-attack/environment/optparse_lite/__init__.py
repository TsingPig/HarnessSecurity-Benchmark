"""Long-option parser package for the legacy maintenance utility."""
from __future__ import annotations

from .errors import ParserError, OptionError
from .tokens import is_long, split_option
from .parser import parse
from .spec import parse_typed
from .cli import load_schema

__all__ = [
    "ParserError",
    "OptionError",
    "is_long",
    "split_option",
    "parse",
    "parse_typed",
    "load_schema",
]
