"""Positional/flag/long-option parsing for the maintenance utility.

The bug: a ``--key=value`` token is recorded as a single boolean flag named ``key=value``
instead of setting ``key`` to ``value``. Use the provided ``tokens.split_option`` helper to
split a long option on the first ``=`` so ``--out=report.txt`` sets ``out`` to ``report.txt``,
while a bare ``--verbose`` stays boolean.
"""
from __future__ import annotations

from .tokens import is_long


def parse(argv):
    """Parse ``argv`` into ``{"options": {...}, "positional": [...]}``."""
    options = {}
    positional = []
    for token in argv:
        if is_long(token):
            options[token[2:]] = True
        else:
            positional.append(token)
    return {"options": options, "positional": positional}
