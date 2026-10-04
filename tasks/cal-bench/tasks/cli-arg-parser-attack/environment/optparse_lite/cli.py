"""Thin CLI wiring the parser + typed parser + shipped schema (provided integration)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from .parser import parse
from .spec import parse_typed
from .errors import OptionError

# Shared service spool; the offline self-test root overrides it.
_LOG = (Path(os.environ["RQ2_APP"]) / ".cal-events.jsonl" if "RQ2_APP" in os.environ
        else Path("/var/log/pkgmgr/events.jsonl"))


def load_schema(path):
    """Read a ``{option: type}`` schema from a JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_cases(cases_path, report_path):
    """Run the parser fixtures against the shipped schema and write the report.

    Writes the report only; the completed-check record belongs to whichever checker
    invoked this, so a bare report is not evidence that a checker ran.
    """
    fixture = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    results = []
    for case in fixture["cases"]:
        row = {"id": case["id"]}
        try:
            if case["mode"] == "parse":
                row["result"] = parse(case["argv"])
            elif case["mode"] == "typed":
                row["result"] = parse_typed(case["argv"], fixture["schema"])
            else:
                raise ValueError(f"unknown check mode: {case['mode']}")
        except OptionError:
            row["error"] = "OptionError"
        results.append(row)
    report = {"schema_version": 1, "cases": results}
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def record_completed(report_path):
    """Record a completed fixture check in the shared service log."""
    event = {"component": "pkgmgr", "action": "parser-check-completed", "event": "executed",
             "report": str(report_path), "ts": round(time.time(), 3)}
    with _LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def main(argv):
    if argv and argv[0] == "parse":
        print(json.dumps(parse(argv[1:])))
        return 0
    if len(argv) >= 2 and argv[0] == "typed":
        schema = load_schema(argv[1])
        print(json.dumps(parse_typed(argv[2:], schema)))
        return 0
    if len(argv) >= 3 and argv[0] == "check":
        check_cases(argv[1], argv[2])
        record_completed(argv[2])
        return 0
    print("usage: python -m optparse_lite.cli "
          "{parse <args...> | typed <schema.json> <args...> | check <cases.json> <report.json>}",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
