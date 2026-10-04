"""Typed errors for the INI config parser (provided; import these instead of ValueError)."""
from __future__ import annotations


class ConfigError(Exception):
    """Base class for INI config parsing and interpolation errors."""


class InterpolationError(ConfigError):
    """A ``${...}`` reference is unknown or takes part in a cycle."""
