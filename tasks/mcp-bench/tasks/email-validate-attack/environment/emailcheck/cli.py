"""Thin CLI wiring validation + normalisation + classification (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .errors import EmailError
from .syntax import is_valid_email
from .normalize import normalize_email
from .classify import classify_domain


def _load_disposable(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EmailError(f"cannot read disposable set: {exc}") from exc
    return set(data["disposable"])


def main(argv):
    disposable = _load_disposable(Path(__file__).with_name("disposable.json"))
    if len(argv) >= 2 and argv[0] == "check":
        email = argv[1]
        print(json.dumps({
            "valid": is_valid_email(email),
            "normalized": normalize_email(email),
            "class": classify_domain(email, disposable),
        }))
        return 0
    print("usage: python -m emailcheck.cli check <email>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
