"""Containment policy for the file service. Implement ``is_allowed``."""
from __future__ import annotations

import posixpath


def is_allowed(base, path):
    """Return ``True`` only if ``path`` is ``base`` itself or a descendant of ``base``.

    Both are absolute POSIX paths. Normalize both before comparing so a ``..`` segment cannot
    sneak the path out of ``base``.
    """
    raise NotImplementedError("is_allowed is not implemented yet")
