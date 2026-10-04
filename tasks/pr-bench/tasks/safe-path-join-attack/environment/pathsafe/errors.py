"""Typed errors for the path-safety package (provided; import these instead of ValueError)."""
from __future__ import annotations


class PathError(Exception):
    """A requested path escapes its authorized base directory."""
