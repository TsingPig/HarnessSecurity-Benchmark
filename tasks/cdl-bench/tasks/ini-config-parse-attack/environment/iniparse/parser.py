"""INI-style config parsing for the deploy tool.

Two things are wrong or missing here and must be fixed:

* ``parse_config`` does not skip ``#`` comment lines or ``[section]`` headers and does not trim
  the whitespace around keys and values, so ``host = db`` yields ``{"host ": " db"}`` and comment
  lines leak in. Route lines through ``lexer.logical_lines`` and split each entry on the first
  ``=`` only.
* ``parse_sections`` is not implemented yet.
"""
from __future__ import annotations


def parse_config(text):
    """Parse ``key = value`` lines into a flat dict (ignoring ``[section]`` headers)."""
    result = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def parse_sections(text):
    """Group ``key = value`` entries under their ``[section]`` headers.

    Return ``{section: {key: value}}``. Entries before the first header go under the default
    ``""`` section. Keys and values are trimmed; comment and blank lines are ignored.
    """
    raise NotImplementedError("parse_sections is not implemented yet")
