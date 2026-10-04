"""CLI wiring score + replay + calibrate (provided integration)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .score import score
from .replay import replay
from .calibrate import calibrate


def main(argv):
    if len(argv) >= 2 and argv[0] == "run":
        spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        events, weights = spec["events"], spec["weights"]
        print(json.dumps({"score": score(events, weights), "replay": replay(events, weights),
                          "calibrated": calibrate(weights)}))
        return 0
    print("usage: python -m scoring.cli run <spec.json>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
