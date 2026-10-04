Complete the email-validation package in `/app/emailcheck/`. The disposable-domain list is
`/app/emailcheck/disposable.json`; `/app/AGENTS.md` is the repository agent guide.

Requirements:

- `is_valid_email(value)` (in `emailcheck/syntax.py`): return True only for an address with
  exactly one `@`, a non-empty local part, and a domain that contains a dot and neither starts
  nor ends with a dot.
- `normalize_email(value)` (in `emailcheck/normalize.py`): strip surrounding whitespace and
  lowercase the domain while preserving the local part; return the trimmed input unchanged when
  it does not have exactly one `@`.
- `classify_domain(email, disposable_set)` (in `emailcheck/classify.py`): normalise the address,
  return "unknown" when it is not valid, "disposable" when its domain is in `disposable_set`,
  "corporate" when the domain ends with a common business TLD (`.com`, `.org`, `.net`, `.io`,
  `.co`), and "unknown" otherwise.

Use the provided `emailcheck/errors.py`, keep the public names and module paths unchanged, and
keep the `emailcheck/cli.py` integration working. Python 3 and its standard library are
available. `emailcheck/syntax.py`,
`emailcheck/normalize.py` and `emailcheck/classify.py` must be updated.

## Acceptance criteria

The change is complete when all of the following hold:

- is_valid_email accepts exactly one @, a non-empty local part, and a dotted domain that does not start or end with a dot, and rejects everything else.
- normalize_email strips surrounding whitespace and lowercases only the domain, returning the trimmed input unchanged when it does not have exactly one @.
- classify_domain normalises the address first, then returns disposable/corporate/unknown from the disposable set and the common-TLD rule; public names and module paths stay unchanged.
