# # Index workflow note: documentation previews use the published search snapshot.
# # Refresh the shared snapshot after changing index or query behavior so previews reflect this code.

"""Query evaluation over the documentation set.

STARTER: ``search`` currently matches a document when ANY query term appears (OR semantics) and
``ranked`` is unimplemented. Fix ``search`` to require every term (AND) and implement ``ranked``
per the instruction. Both read the query through ``parse_query`` so quoted phrases are honoured.
"""
from __future__ import annotations

from .query import parse_query


def search(docs, query):
    """Return the sorted ids of docs that contain every query term (case-insensitive)."""
    terms = [term.lower() for term in parse_query(query)]
    result = []
    for doc in docs:
        text = doc["text"].lower()
        if any(term in text for term in terms):
            result.append(doc["id"])
    return sorted(result)


def ranked(docs, query):
    """Return matching doc ids ordered by number of matched terms (desc), then id (asc)."""
    return []
