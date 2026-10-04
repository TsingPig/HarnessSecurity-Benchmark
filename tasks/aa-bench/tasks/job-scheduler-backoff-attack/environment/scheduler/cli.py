"""CLI wiring the backoff schedule and retry policy together (provided integration)."""
from __future__ import annotations

import json
import sys

from .backoff import next_delay, retry_schedule
from .policy import should_retry


def main(argv):
    if len(argv) >= 2 and argv[0] == "schedule":
        print(json.dumps(retry_schedule(int(argv[1]))))
        return 0
    if len(argv) >= 4 and argv[0] == "retry":
        print("retry" if should_retry(argv[1], int(argv[2]), int(argv[3])) else "stop")
        return 0
    print("usage: python -m scheduler.cli {schedule <n> | retry <status> <attempt> <max>}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
