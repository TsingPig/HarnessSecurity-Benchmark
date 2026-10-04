"""CLI wiring scan + redact into a report (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .report import redaction_report


def main(argv):
    if len(argv) >= 2 and argv[0] == "report":
        record = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        print(json.dumps(redaction_report(record)))
        return 0
    print("usage: python -m redactor.cli report <record.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
