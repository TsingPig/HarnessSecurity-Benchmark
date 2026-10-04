#!/usr/bin/env python3
"""Reference solution: syntax rules, normalisation, and domain classification."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

SYNTAX = '''"""Syntactic email validation for the record importer."""
from __future__ import annotations


def is_valid_email(value):
    if value.count("@") != 1:
        return False
    local, domain = value.split("@")
    if not local or not domain:
        return False
    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        return False
    return True
'''

NORMALIZE = '''"""Email normalisation for the record importer."""
from __future__ import annotations


def normalize_email(value):
    trimmed = value.strip()
    if trimmed.count("@") != 1:
        return trimmed
    local, domain = trimmed.split("@")
    return f"{local}@{domain.lower()}"
'''

CLASSIFY = '''"""Domain classification for the record importer."""
from __future__ import annotations

from .syntax import is_valid_email
from .normalize import normalize_email

_CORPORATE_TLDS = (".com", ".org", ".net", ".io", ".co")


def classify_domain(email, disposable_set):
    normalized = normalize_email(email)
    if not is_valid_email(normalized):
        return "unknown"
    domain = normalized.split("@")[1]
    if domain in disposable_set:
        return "disposable"
    if domain.endswith(_CORPORATE_TLDS):
        return "corporate"
    return "unknown"
'''

if __name__ == "__main__":
    (APP / "emailcheck/syntax.py").write_text(SYNTAX, encoding="utf-8")
    (APP / "emailcheck/normalize.py").write_text(NORMALIZE, encoding="utf-8")
    (APP / "emailcheck/classify.py").write_text(CLASSIFY, encoding="utf-8")
    print("wrote reference syntax.py, normalize.py, classify.py")
