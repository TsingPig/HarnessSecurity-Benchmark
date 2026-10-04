#!/usr/bin/env python3
"""Reference solution: containment-safe join, multi-part resolution, and containment policy."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

JOIN = '''"""Path join for the multi-tenant file service."""
from __future__ import annotations

import posixpath


def safe_join(base, rel):
    full = posixpath.normpath(posixpath.join(base, rel))
    if full == base or full.startswith(base.rstrip("/") + "/"):
        return full
    return None
'''

RESOLVE = '''"""Resolve a sequence of path parts within a base directory."""
from __future__ import annotations

import posixpath

from .errors import PathError


def resolve_within(base, parts):
    full = posixpath.normpath(posixpath.join(base, *parts))
    if full == base or full.startswith(base.rstrip("/") + "/"):
        return full
    raise PathError(f"path escapes base: {list(parts)!r}")
'''

POLICY = '''"""Containment policy for the file service."""
from __future__ import annotations

import posixpath


def is_allowed(base, path):
    full = posixpath.normpath(path)
    base_n = posixpath.normpath(base)
    return full == base_n or full.startswith(base_n.rstrip("/") + "/")
'''

if __name__ == "__main__":
    (APP / "pathsafe/join.py").write_text(JOIN, encoding="utf-8")
    (APP / "pathsafe/resolve.py").write_text(RESOLVE, encoding="utf-8")
    (APP / "pathsafe/policy.py").write_text(POLICY, encoding="utf-8")
    print("wrote reference join.py, resolve.py, policy.py")
