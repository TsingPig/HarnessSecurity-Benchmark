"""Documentation search package: tokenizer, inverted index, AND search, ranking, query parsing."""
from __future__ import annotations

from .errors import QueryError
from .tokenize import tokenize
from .index import build_index
from .query import parse_query
from .search import search, ranked

__all__ = ["QueryError", "tokenize", "build_index", "parse_query", "search", "ranked"]
