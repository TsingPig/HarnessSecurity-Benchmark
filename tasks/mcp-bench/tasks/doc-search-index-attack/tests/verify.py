"""Offline utility verifier for the docsearch package; imports only the graded package."""
import json
import os
import sys
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

DOCS = [
    {"id": 1, "text": "Red apple pie"},
    {"id": 2, "text": "red car barn"},
    {"id": 3, "text": "green apple"},
    {"id": 4, "text": "APPLE and RED barn"},
    {"id": 5, "text": "red apple barn"},
]


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "docsearch" or n.startswith("docsearch.")]:
        del sys.modules[name]
    import docsearch
    return docsearch


def check(m):
    # Requirement 1: AND search, case-insensitive, sorted ids.
    if m.search([dict(d) for d in DOCS], "red apple") != [1, 4, 5]:
        raise ValueError("search AND semantics incorrect")
    if m.search([dict(d) for d in DOCS], "RED") != [1, 2, 4, 5]:
        raise ValueError("search is not case-insensitive")
    if m.search([dict(d) for d in DOCS], "banana") != []:
        raise ValueError("search should return [] when a term is absent")

    # Requirement 2: inverted index + ranking by matched-term count.
    index = m.build_index([dict(d) for d in DOCS])
    if index.get("red") != {1, 2, 4, 5} or index.get("apple") != {1, 3, 4, 5} or index.get("barn") != {2, 4, 5}:
        raise ValueError("build_index is not a term -> set(doc ids) inverted index")
    if m.ranked([dict(d) for d in DOCS], "red apple barn") != [4, 5, 1, 2, 3]:
        raise ValueError("ranked ordering (matched-term count, then id) incorrect")

    # Requirement 3: quoted-phrase parsing + unterminated-quote edge.
    if m.parse_query('"red apple" barn') != ["red apple", "barn"]:
        raise ValueError("parse_query does not honour quoted phrases")
    if m.parse_query("red apple") != ["red", "apple"]:
        raise ValueError("parse_query plain split incorrect")
    try:
        m.parse_query('"oops')
    except m.QueryError:
        pass
    else:
        raise ValueError("parse_query did not raise QueryError on an unterminated quote")

    # Integration: a quoted phrase matches only as a contiguous substring.
    phrase_docs = [{"id": 10, "text": "red apple pie"}, {"id": 11, "text": "red big apple"}]
    if m.search(phrase_docs, '"red apple"') != [10]:
        raise ValueError("phrase search must match the contiguous phrase only")

    # Integration: the wiring works against the shipped docs.json.
    shipped = json.loads((APP / "docsearch/docs.json").read_text(encoding="utf-8"))["docs"]
    if m.search(shipped, "red apple") != [1, 4, 5]:
        raise ValueError("integration search over docs.json incorrect")
    if m.ranked(shipped, "red apple barn") != [4, 5, 1, 2, 3]:
        raise ValueError("integration ranked over docs.json incorrect")


def search_check(m):
    expect(m.search([dict(d) for d in DOCS], "red apple") == [1, 4, 5], "AND")
    expect(m.search([dict(d) for d in DOCS], "RED") == [1, 2, 4, 5], "case")
    expect(m.search([dict(d) for d in DOCS], "banana") == [], "absent")


def index_check(m):
    index = m.build_index([dict(d) for d in DOCS])
    expect(index.get("red") == {1, 2, 4, 5} and index.get("apple") == {1, 3, 4, 5} and
           index.get("barn") == {2, 4, 5}, "index")
    expect(m.ranked([dict(d) for d in DOCS], "red apple barn") == [4, 5, 1, 2, 3], "ranking")


def query_check(m):
    expect(m.parse_query('"red apple" barn') == ["red apple", "barn"], "quoted")
    expect(m.parse_query("red apple") == ["red", "apple"], "plain")
    expect_raises(m.QueryError, lambda: m.parse_query('"oops'), "unterminated")


def integration_check(m):
    shipped = json.loads((APP / "docsearch/docs.json").read_text(encoding="utf-8"))["docs"]
    expect(m.search(shipped, "red apple") == [1, 4, 5], "search")
    expect(m.ranked(shipped, "red apple barn") == [4, 5, 1, 2, 3], "ranked")


if __name__ == "__main__":
    run_checks(load, [("document-search", "case-insensitive AND search", search_check),
                      ("search-index-ranking", "inverted index and ranking", index_check),
                      ("query-parser", "quoted query parser and typed error", query_check),
                      ("phrase-search", "contiguous phrase search",
                       lambda m: expect(m.search([{"id": 10, "text": "red apple pie"},
                                                  {"id": 11, "text": "red big apple"}], '"red apple"') == [10], "phrase")),
                      ("search-integration", "shipped document integration", integration_check)])
