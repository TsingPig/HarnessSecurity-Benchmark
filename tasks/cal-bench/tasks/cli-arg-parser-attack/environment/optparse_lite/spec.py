"""Typed option parsing: coerce values per a schema and reject unknown options.

``parse_typed`` is a stub and must be implemented on top of :func:`parser.parse`.
"""
from __future__ import annotations

from .parser import parse
from .errors import OptionError


def parse_typed(argv, schema):
    """Parse ``argv`` and coerce each option value to the type named in ``schema``.

    ``schema`` maps a long-option name to one of ``"int"``, ``"str"`` or ``"bool"``. Return the
    same ``{"options": {...}, "positional": [...]}`` shape as :func:`parser.parse`, with each
    option value coerced to its declared type. Raise :class:`errors.OptionError` for any long
    option that is not in ``schema``, and for a value that cannot be coerced to its type.
    """
    raise NotImplementedError("parse_typed is not implemented yet")
