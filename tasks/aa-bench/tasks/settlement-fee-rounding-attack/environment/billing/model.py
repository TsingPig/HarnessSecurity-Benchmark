"""Load a settlement batch from a JSON ledger file (provided; do not rewrite)."""
from __future__ import annotations

import json
from pathlib import Path

from .errors import MalformedEntryError


def parse_entries(path):
    """Return the ledger entries from ``{"entries": [...]}`` at ``path``.

    Each entry must carry an ``account`` and an integer ``amount_cents`` (credit positive, debit
    negative); ``fee_bps`` is optional and defaults to 0. A row missing the required fields
    raises :class:`billing.errors.MalformedEntryError`.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = []
    for row in data.get("entries", []):
        if "account" not in row or "amount_cents" not in row:
            raise MalformedEntryError(f"entry missing account/amount_cents: {row!r}")
        entries.append({
            "account": row["account"],
            "amount_cents": int(row["amount_cents"]),
            "fee_bps": int(row.get("fee_bps", 0)),
        })
    return entries
