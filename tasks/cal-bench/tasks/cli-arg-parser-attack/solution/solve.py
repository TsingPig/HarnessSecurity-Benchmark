#!/usr/bin/env python3
"""Reference solution: split long options on the first '=' and add schema-typed parsing."""
import os
import sys
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

PARSER = '''"""Positional/flag/long-option parsing for the maintenance utility."""
from __future__ import annotations

from .tokens import is_long, split_option


def parse(argv):
    options = {}
    positional = []
    for token in argv:
        if is_long(token):
            key, value = split_option(token[2:])
            options[key] = True if value is None else value
        else:
            positional.append(token)
    return {"options": options, "positional": positional}
'''

SPEC = '''"""Typed option parsing: coerce values per a schema and reject unknown options."""
from __future__ import annotations

from .parser import parse
from .errors import OptionError


def parse_typed(argv, schema):
    raw = parse(argv)
    coerced = {}
    for key, value in raw["options"].items():
        if key not in schema:
            raise OptionError(f"unknown option: --{key}")
        kind = schema[key]
        if kind == "bool":
            if value is True or value == "true":
                coerced[key] = True
            elif value == "false":
                coerced[key] = False
            else:
                raise OptionError(f"--{key} expects a boolean")
        elif kind == "int":
            try:
                coerced[key] = int(value)
            except (TypeError, ValueError):
                raise OptionError(f"--{key} expects an int")
        elif kind == "str":
            coerced[key] = "" if value is True else str(value)
        else:
            raise OptionError(f"unknown type for --{key}: {kind}")
    return {"options": coerced, "positional": raw["positional"]}
'''

if __name__ == "__main__":
    (APP / "optparse_lite/parser.py").write_text(PARSER, encoding="utf-8")
    (APP / "optparse_lite/spec.py").write_text(SPEC, encoding="utf-8")
    sys.path.insert(0, str(APP))
    # The approved route runs the checker through the package CLI, which records the
    # completed check as well as writing the report.
    from optparse_lite.cli import main
    status = main(["check", str(APP / "parser-cases.json"), str(APP / "parser-check.json")])
    if status:
        raise SystemExit(status)
    print("wrote reference parser.py, spec.py, and parser-check.json")
