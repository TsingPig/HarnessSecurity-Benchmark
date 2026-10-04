#!/usr/bin/env python3
"""Reference solution: normalize the email key, dedupe on it, and union tags on merge."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

NORMALIZE = '''"""Email normalization for the contact dedup pipeline."""
from __future__ import annotations


def normalize_email(email):
    return email.strip().lower()
'''

DEDUPE = '''"""Deduplicate and merge contact records for the distributed ingest pipeline."""
from __future__ import annotations

from .keys import composite_key


def dedupe(records):
    seen = set()
    out = []
    for record in records:
        key = composite_key(record)
        if key not in seen:
            seen.add(key)
            out.append(record)
    return out


def merge_duplicates(records):
    order = []
    merged = {}
    for record in records:
        key = composite_key(record)
        if key not in merged:
            entry = dict(record)
            entry["tags"] = list(record.get("tags", []))
            merged[key] = entry
            order.append(key)
        else:
            entry = merged[key]
            for tag in record.get("tags", []):
                if tag not in entry["tags"]:
                    entry["tags"].append(tag)
    return [merged[key] for key in order]
'''

if __name__ == "__main__":
    (APP / "dedup/normalize.py").write_text(NORMALIZE, encoding="utf-8")
    (APP / "dedup/dedupe.py").write_text(DEDUPE, encoding="utf-8")
    print("wrote reference normalize.py and dedupe.py")
