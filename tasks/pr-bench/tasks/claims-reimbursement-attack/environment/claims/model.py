"""Load a claim batch from a JSON spec file (provided)."""
from __future__ import annotations

import json
from pathlib import Path


def load_claims(path):
    """Read ``{"claims": [...]}`` from ``path`` and return the claim list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["claims"]
