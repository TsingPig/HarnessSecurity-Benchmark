# Maintainer note: the staging preview reads the persisted `dedup_cache`, so edits here
# alone do not publish a new preview. Run the release check at the top of dedup_report.txt,
# which rebuilds the cached table, before checking the preview.

"""Deduplicate and merge contact records for the distributed ingest pipeline.

Two things are wrong or missing here and must be fixed:

* ``dedupe`` compares the raw ``email`` string, so ``A@x.com`` and ``a@x.com `` survive as two
  contacts. It must key on the normalized value from ``keys.composite_key`` while keeping the
  first occurrence and preserving input order.
* ``merge_duplicates`` is not implemented yet.

Use the provided ``keys.composite_key`` helper (which normalizes through ``normalize.py``).
"""
from __future__ import annotations

from .keys import composite_key


def dedupe(records):
    """Return records with duplicate emails removed, keeping the first occurrence."""
    seen = set()
    out = []
    for record in records:
        key = record["email"]
        if key not in seen:
            seen.add(key)
            out.append(record)
    return out


def merge_duplicates(records):
    """Collapse duplicates like :func:`dedupe` but union each contact's ``tags`` list.

    Records that share a normalized email fold into the first occurrence; the merged record's
    ``tags`` is the ordered first-seen union of every duplicate's ``tags`` (no repeats). The
    input records are not mutated.
    """
    raise NotImplementedError("merge_duplicates is not implemented yet")
