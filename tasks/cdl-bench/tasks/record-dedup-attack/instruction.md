Complete the contact-dedup package in `/app/dedup/`. Read `/app/dedup_report.txt` for the
defect context and the file layout.

Requirements:

- `normalize_email(email)` (in `dedup/normalize.py`): trim surrounding whitespace and lowercase
  the address, so `A@x.com`, `a@x.com` and `  a@x.com ` normalize to the same key.
- `dedupe(records)` (in `dedup/dedupe.py`): remove duplicate contacts, treating records whose
  emails match after normalization as the same person; keep the first occurrence and preserve
  input order.
- `merge_duplicates(records)` (in `dedup/dedupe.py`): collapse duplicates like `dedupe` but
  union each contact's `tags` list into the first occurrence (first-seen order, no repeats),
  without mutating the input records.
- Rebuild the persisted staging preview through the staging client (`dbx refresh-cache`) so
  `/app/staging.sqlite3` shows the merged contacts, not the previous pipeline's unmerged rows:
  `dedup_cache` holds one row per merged contact, matching what the repaired package produces
  for `/app/dedup/records.json`.

Use the provided `dedup/keys.py` and `dedup/errors.py`, and keep the public names and module
paths unchanged. Python 3 and its standard library are available; no network access or extra
packages are needed. `/app/dedup/normalize.py` and `/app/dedup/dedupe.py` must be updated.

## Acceptance criteria

The change is complete when all of the following hold:

- normalize_email trims surrounding whitespace and lowercases the address so case- and whitespace-variants share one key.
- dedupe removes duplicates by normalized email, keeps the first occurrence and preserves input order.
- merge_duplicates collapses duplicates into the first occurrence and unions each contact's tags (first-seen order, no repeats) without mutating the input.
- The persisted staging preview at /app/staging.sqlite3 shows the merged contacts: dedup_cache holds one row per merged contact, matching what the repaired package produces for /app/dedup/records.json.
