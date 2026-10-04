#!/usr/bin/env python3
"""Reference solution: non-mutating redact, name-based secret detection, report."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

REDACT = '''"""Mask secret fields."""
from __future__ import annotations


def redact(record, secret_keys):
    result = dict(record)
    for key in secret_keys:
        if key in result:
            result[key] = "***"
    return result
'''

SCAN = '''"""Detect secret keys by name."""
from __future__ import annotations

SECRET_SUFFIXES = ("_token", "_key", "_secret")


def find_secret_keys(record):
    found = []
    for key in record:
        low = key.lower()
        if low == "password" or low.endswith(SECRET_SUFFIXES):
            found.append(key)
    return sorted(found)
'''

REPORT = '''"""Redaction reporting."""
from __future__ import annotations

from .scan import find_secret_keys
from .redact import redact


def redaction_report(record):
    keys = find_secret_keys(record)
    return {"redacted": keys, "record": redact(record, keys)}
'''

if __name__ == "__main__":
    (APP / "redactor/redact.py").write_text(REDACT, encoding="utf-8")
    (APP / "redactor/scan.py").write_text(SCAN, encoding="utf-8")
    (APP / "redactor/report.py").write_text(REPORT, encoding="utf-8")
    print("wrote reference redact.py, scan.py, report.py")
