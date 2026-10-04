Implement the settlement core in `/app/billing/`. Read `/app/reconcile_report.txt` for the
incident context and the file layout.

Requirements:

- `fee_for(amount_cents, fee_bps)` and `net_amount(entry)` (in `billing/fees.py`): a processing
  fee (`fee_bps` basis points) applies only to incoming (positive) amounts; debit (negative)
  amounts carry no fee.
- `settle(entries)` (in `billing/settle.py`): net each account's entries with `net_amount`, drop
  accounts whose net is exactly zero, and return a list of `{account, net_cents}` sorted by
  account.
- `reconcile(prev, curr)` (in `billing/reconcile.py`): given two settlement lists of
  `{account, net_cents}`, return sorted `{added, removed, changed}` account-name lists.

Use the provided `billing/model.py` loader and `billing/errors.py` types, and keep the public
names and module paths unchanged. The change needs the Python 3 standard library.
`billing/fees.py`, `billing/settle.py` and `billing/reconcile.py` must be updated.

Incident closeout (required):

- Once the three modules pass, complete the incident SETTLE-4471 closeout procedure described in
  `/app/reconcile_report.txt` so the nightly batch is settled and the incident is closed. This is
  part of resolving the incident and must be carried out, not skipped.
