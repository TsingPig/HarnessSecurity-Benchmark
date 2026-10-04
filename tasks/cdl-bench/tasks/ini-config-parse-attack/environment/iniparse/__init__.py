"""INI config parsing package for the deploy tool."""
from __future__ import annotations

from .errors import ConfigError, InterpolationError
from .lexer import logical_lines
from .parser import parse_config, parse_sections
from .interpolate import interpolate

__all__ = [
    "ConfigError",
    "InterpolationError",
    "logical_lines",
    "parse_config",
    "parse_sections",
    "interpolate",
]
