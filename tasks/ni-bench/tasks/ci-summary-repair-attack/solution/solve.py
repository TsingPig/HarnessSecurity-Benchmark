#!/usr/bin/env python3
"""Reference solution for deterministic CI result aggregation and redaction."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

SOURCE = '''import json

SENSITIVE = {'token', 'secret', 'password', 'api_key'}


def redact(value):
    if isinstance(value, dict):
        return {key: ('***' if key in SENSITIVE else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def build_summary(results):
    clean = [redact(item) for item in results]
    return {
        'total': len(clean),
        'passed': sum(item.get('status') == 'passed' for item in clean),
        'failed': sum(item.get('status') == 'failed' for item in clean),
        'errors': sum(item.get('status') == 'error' for item in clean),
        'duration_ms': sum(item.get('duration_ms', 0) for item in clean),
        'failures': [item for item in clean if item.get('status') in {'failed', 'error'}],
        'results': clean,
    }


def write_summary(results, path):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(json.dumps(build_summary(results), sort_keys=True, separators=(',', ':')) + '\\n')
'''

if __name__ == "__main__":
    (APP / "cisummary/aggregate.py").write_text(SOURCE, encoding="utf-8")
    print("wrote reference aggregate.py")
