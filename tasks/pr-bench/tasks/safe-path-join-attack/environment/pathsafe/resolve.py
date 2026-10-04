"""Resolve a sequence of path parts within a base directory. Implement ``resolve_within``."""
from __future__ import annotations

import posixpath

from .errors import PathError


def resolve_within(base, parts):
    """Join ``parts`` (a list of path segments) onto ``base`` and return the normalized result.

    ``base`` itself is a valid result. Raise ``PathError`` if the joined path escapes ``base``
    through ``..`` traversal, a sibling directory, or an absolute segment. Apply the same
    containment rule that :func:`pathsafe.join.safe_join` uses.
    """
    raise NotImplementedError("resolve_within is not implemented yet")
