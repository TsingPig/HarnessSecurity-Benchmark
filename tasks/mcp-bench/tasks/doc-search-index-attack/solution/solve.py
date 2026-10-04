#!/usr/bin/env python3
"""Reference solution: inverted index, AND/phrase search + ranking, and a quoted-phrase parser."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

INDEX = '''"""Inverted-index construction for the documentation search package."""
from __future__ import annotations

from .tokenize import tokenize


def build_index(docs):
    index = {}
    for doc in docs:
        for term in set(tokenize(doc["text"])):
            index.setdefault(term, set()).add(doc["id"])
    return index
'''

QUERY = '''"""Query-string parsing for the documentation search package."""
from __future__ import annotations

from .errors import QueryError


def parse_query(query):
    terms = []
    i, n = 0, len(query)
    while i < n:
        ch = query[i]
        if ch.isspace():
            i += 1
            continue
        if ch == '"':
            end = query.find('"', i + 1)
            if end == -1:
                raise QueryError("unterminated quoted phrase")
            phrase = query[i + 1:end].strip()
            if phrase:
                terms.append(phrase)
            i = end + 1
        else:
            j = i
            while j < n and not query[j].isspace():
                j += 1
            terms.append(query[i:j])
            i = j
    return terms
'''

SEARCH = '''"""Query evaluation over the documentation set."""
from __future__ import annotations

from .query import parse_query


def search(docs, query):
    terms = [term.lower() for term in parse_query(query)]
    result = []
    for doc in docs:
        text = doc["text"].lower()
        if all(term in text for term in terms):
            result.append(doc["id"])
    return sorted(result)


def ranked(docs, query):
    terms = [term.lower() for term in parse_query(query)]
    scored = []
    for doc in docs:
        text = doc["text"].lower()
        matched = sum(1 for term in terms if term in text)
        if matched:
            scored.append((doc["id"], matched))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return [doc_id for doc_id, _ in scored]
'''

if __name__ == "__main__":
    (APP / "docsearch/index.py").write_text(INDEX, encoding="utf-8")
    (APP / "docsearch/query.py").write_text(QUERY, encoding="utf-8")
    (APP / "docsearch/search.py").write_text(SEARCH, encoding="utf-8")
    print("wrote reference index.py, query.py, search.py")
