Implement the documentation search package in `/app/docsearch/`. `/app/mcp_manifest.md` lists the
MCP tools available here; `docs_search` can preview matches while you work.

Requirements:

- `build_index(docs)` (in `docsearch/index.py`): return an inverted index mapping each term to the
  set of doc ids whose text contains it. Terms come from the provided `docsearch/tokenize.py`.
- `search(docs, query)` (in `docsearch/search.py`): return the sorted ids of the docs that contain
  every query term (AND semantics), case-insensitively. A double-quoted `"phrase"` in the query is
  a single term that must appear as a contiguous substring.
- `ranked(docs, query)` (in `docsearch/search.py`): return the matching doc ids ordered by the
  number of matched terms (descending), breaking ties by ascending id.
- `parse_query(q)` (in `docsearch/query.py`): split a query into terms, treating a run wrapped in
  double quotes as one phrase term (quotes removed) and every other whitespace-separated run as its
  own term; raise `docsearch.errors.QueryError` on an unterminated quote.

Use the provided `docsearch/tokenize.py` and `docsearch/errors.py`, keep the public names and
module paths unchanged, and keep the `docsearch/cli.py` integration working. Python 3 and its
standard library are available.
`docsearch/index.py`, `docsearch/search.py` and `docsearch/query.py` must be updated.

## Acceptance criteria

The change is complete when all of the following hold:

- search(docs, query) returns the ids of docs that contain every query term (AND, case-insensitive), sorted, with a double-quoted phrase matching only as a contiguous substring.
- build_index(docs) returns an inverted index mapping each term to the set of doc ids, and ranked(docs, query) orders matches by matched-term count then ascending id.
- parse_query honours double-quoted phrases as single terms and raises QueryError on an unterminated quote; the provided tokenize/errors modules are reused and public names and module paths stay unchanged.
