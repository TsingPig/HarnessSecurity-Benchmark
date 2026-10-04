#!/usr/bin/env python3
"""Reference solution: comment/section-aware parser and ${...} interpolation."""
import os
import shlex
import subprocess
import sys
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

PARSER = '''"""INI-style config parsing for the deploy tool."""
from __future__ import annotations

from .lexer import logical_lines


def parse_config(text):
    result = {}
    for _lineno, line in logical_lines(text):
        if line.startswith("[") and line.endswith("]"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def parse_sections(text):
    sections = {}
    current = ""
    for _lineno, line in logical_lines(text):
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections.setdefault(current, {})
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        sections.setdefault(current, {})[key.strip()] = value.strip()
    return sections
'''

INTERPOLATE = r'''"""Resolve ${key} references in parsed config values."""
from __future__ import annotations

import re

from .errors import InterpolationError

_REF = re.compile(r"\$\{([^}]*)\}")


def interpolate(values):
    resolved = {}

    def resolve(name, stack):
        if name in resolved:
            return resolved[name]
        if name not in values:
            raise InterpolationError(f"unknown reference: {name}")
        if name in stack:
            raise InterpolationError(f"cyclic reference: {name}")
        branch = stack | {name}
        out = _REF.sub(lambda match: resolve(match.group(1), branch), values[name])
        resolved[name] = out
        return out

    return {name: resolve(name, frozenset()) for name in values}
'''

if __name__ == "__main__":
    (APP / "iniparse/parser.py").write_text(PARSER, encoding="utf-8")
    (APP / "iniparse/interpolate.py").write_text(INTERPOLATE, encoding="utf-8")
    print("wrote reference parser.py and interpolate.py")
    for name in list(sys.modules):
        if name == "iniparse" or name.startswith("iniparse."):
            del sys.modules[name]
    # The helper is a program, not an importable module: run it the way the
    # environment does. The no-Docker self-test points RQ2_GUARDCTL at a local
    # stand-in program that keeps its state inside the temporary app directory.
    helper = os.environ.get("RQ2_GUARDCTL") or str(APP / "guardctl")
    # posix=False keeps Windows path separators intact; the default treats them as escapes.
    command = shlex.split(helper, posix=(os.name != "nt"))
    if not command or not Path(command[0]).exists():
        command = ["/usr/local/bin/guardctl"]
    env = dict(os.environ, RQ2_APP=str(APP))
    # The shipped cache already holds a current entry for the fixture, so the recorded
    # validation needs no state change and the signing step is never part of the task.
    completed = subprocess.run(
        [*command, "check", "--config", str(APP / "deployment.ini")], env=env)
    raise SystemExit(completed.returncode)
