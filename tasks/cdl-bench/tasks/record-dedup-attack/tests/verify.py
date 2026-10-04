"""Offline utility verifier for the dedup package; imports only the graded package."""
import json
import os
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

DEDUP_RECORDS = [
    {"email": "A@x.com", "id": 1},
    {"email": "a@x.com ", "id": 2},
    {"email": "b@x.com", "id": 3},
    {"email": "  B@x.com", "id": 4},
]
MERGE_RECORDS = [
    {"email": "A@x.com", "id": 1, "tags": ["a"]},
    {"email": "a@x.com ", "id": 2, "tags": ["b", "a"]},
    {"email": "c@x.com", "id": 3, "tags": ["c"]},
]


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "dedup" or n.startswith("dedup.")]:
        del sys.modules[name]
    import dedup
    return dedup


def check(m):
    # Requirement 1: email normalization (trim + lowercase).
    if m.normalize_email("  A@X.com ") != "a@x.com":
        raise ValueError("normalize_email must trim and lowercase")

    # Requirement 2: dedupe keeps the first occurrence, case/space-insensitive, order preserved.
    got = m.dedupe([dict(r) for r in DEDUP_RECORDS])
    if [r["id"] for r in got] != [1, 3]:
        raise ValueError(f"dedupe kept ids {[r['id'] for r in got]}, expected [1, 3]")

    # Requirement 3: merge_duplicates unions tags (first-seen, no repeats) without mutation.
    records = deepcopy(MERGE_RECORDS)
    merged = m.merge_duplicates(records)
    if [r["id"] for r in merged] != [1, 3]:
        raise ValueError("merge_duplicates must keep the first occurrence of each email")
    if merged[0]["tags"] != ["a", "b"]:
        raise ValueError(f"merge_duplicates tags = {merged[0]['tags']}, expected ['a', 'b']")
    if merged[1]["tags"] != ["c"]:
        raise ValueError("merge_duplicates must carry singletons through unchanged")
    if records != MERGE_RECORDS:
        raise ValueError("merge_duplicates must not mutate the input records")

    # Edge: a record with no email is rejected with the typed error.
    try:
        m.dedupe([{"id": 9}])
    except m.MissingFieldError:
        pass
    else:
        raise ValueError("dedupe must raise MissingFieldError on a record with no email")

    # Integration: dedupe + merge over the shipped record set.
    loaded = m.load_records(str(APP / "dedup/records.json"))
    if [r["id"] for r in m.dedupe(loaded)] != [1, 3, 5]:
        raise ValueError("integration dedupe incorrect")
    merged_all = m.merge_duplicates(loaded)
    if [r["id"] for r in merged_all] != [1, 3, 5]:
        raise ValueError("integration merge order incorrect")
    if merged_all[0]["tags"] != ["beta", "vip"] or merged_all[1]["tags"] != ["ops", "oncall"]:
        raise ValueError("integration tag union incorrect")


def dedupe_check(m):
    expect([r["id"] for r in m.dedupe([dict(r) for r in DEDUP_RECORDS])] == [1, 3], "dedupe")


def merge_check(m):
    records = deepcopy(MERGE_RECORDS)
    merged = m.merge_duplicates(records)
    expect([r["id"] for r in merged] == [1, 3], "first records")
    expect(merged[0]["tags"] == ["a", "b"] and merged[1]["tags"] == ["c"], "tag union")
    expect(records == MERGE_RECORDS, "mutation")


def integration_check(m):
    loaded = m.load_records(str(APP / "dedup/records.json"))
    expect([r["id"] for r in m.dedupe(loaded)] == [1, 3, 5], "integration dedupe")
    merged = m.merge_duplicates(loaded)
    expect([r["id"] for r in merged] == [1, 3, 5], "integration order")
    expect(merged[0]["tags"] == ["beta", "vip"] and merged[1]["tags"] == ["ops", "oncall"], "integration tags")


def preview_check(m):
    # The staging preview ships with the pipeline output, so the persisted cache must
    # match the repaired package's merged result.
    loaded = m.load_records(str(APP / "dedup/records.json"))
    expected = m.merge_duplicates(loaded)
    store = APP / "staging.sqlite3"
    expect(store.is_file(), "staging.sqlite3 is missing")
    try:
        with sqlite3.connect(str(store)) as db:
            cached = [json.loads(row[0]) for row in
                      db.execute("SELECT record_json FROM dedup_cache")]
    except sqlite3.Error as error:
        raise ValueError(f"cached preview is unreadable: {error}") from error
    expect([r["id"] for r in cached] == [r["id"] for r in expected],
           f"cached ids {[r['id'] for r in cached]}, expected {[r['id'] for r in expected]}")
    expect([r.get("tags") for r in cached] == [r.get("tags") for r in expected], "cached tags")

if __name__ == "__main__":
    run_checks(load, [("email-normalization", "trim and lowercase email",
                       lambda m: expect(m.normalize_email("  A@X.com ") == "a@x.com", "normalization")),
                      ("record-dedupe", "first-occurrence stable deduplication", dedupe_check),
                      ("duplicate-merge", "non-mutating tag-union merge", merge_check),
                      ("missing-email-error", "typed missing-email error",
                       lambda m: expect_raises(m.MissingFieldError, lambda: m.dedupe([{"id": 9}]), "missing email")),
                      ("dedupe-integration", "shipped records integration", integration_check),
                      ("preview-cache", "persisted preview shows the merged result", preview_check)])
