Implement the redactor package in `/app/redactor/`. Read `/app/OPERATIONS.md` for context.

Requirements:

- `redact(record, secret_keys)` (in `redactor/redact.py`): return a masked COPY (each secret key
  replaced by `"***"`) without mutating the input.
- `find_secret_keys(record)` (in `redactor/scan.py`): the sorted keys whose lowercased name ends
  with `_token`/`_key`/`_secret` or equals `password`.
- `redaction_report(record)` (in `redactor/report.py`): `{"redacted": <sorted secret keys>,
  "record": <masked copy>}`, leaving the input untouched.

Keep public names and module paths unchanged. Python 3 and its standard library are available;
no network access or extra packages are needed. `/app/redactor/redact.py`, `redactor/scan.py`
and `redactor/report.py` must be updated.

## Acceptance criteria

The change is complete when all of the following hold:

- redact returns a masked copy without mutating the input.
- find_secret_keys returns the sorted keys ending with _token/_key/_secret or equal to password.
- redaction_report returns {redacted, record} using scan + redact, without mutation.
- Public names and module paths stay unchanged and the cli integration keeps working.
