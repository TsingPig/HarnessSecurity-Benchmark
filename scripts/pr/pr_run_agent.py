"""Validate or run the published PR benchmark."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
from entrypoint import main

if __name__ == "__main__":
    result = main("pr")
    raise SystemExit(0 if result.get("status", "completed") in ("validated", "planned", "completed") else 1)
