"""Inverted-index construction for the documentation search package.

STARTER: this builds a per-document term map instead of an inverted index, so callers cannot
look documents up by term. Implement ``build_index`` per the instruction.
"""
from __future__ import annotations

from .tokenize import tokenize


def build_index(docs):
    """Return a mapping from term to the set of doc ids that contain it."""
    index = {}
    for doc in docs:
        index[doc["id"]] = set(tokenize(doc["text"]))
    return index
