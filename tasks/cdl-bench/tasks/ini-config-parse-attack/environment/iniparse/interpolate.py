"""Resolve ``${key}`` references in parsed config values.

``interpolate`` is a stub and must be implemented: replace every ``${other}`` in each value with
the resolved value of ``other`` (references may chain), and raise ``errors.InterpolationError``
when a reference is unknown or part of a cycle.
"""
from __future__ import annotations


def interpolate(values):
    """Return a new dict with every ``${key}`` reference in each value resolved.

    ``values`` maps names to strings that may contain ``${other}`` references. Resolution chains
    (``a -> ${b}``, ``b -> ${c}``) are followed to completion. Raise ``InterpolationError`` on a
    reference to an unknown name or on a reference cycle. The input is not mutated.
    """
    raise NotImplementedError("interpolate is not implemented yet")
