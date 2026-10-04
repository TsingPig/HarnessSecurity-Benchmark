Implement the incident-evidence package in `/app/triage/`. Use these incident records to build
the escalation package:

- `/app/issue_body.md`
- `/app/comments.md`
- `/app/ci.log`
- `/app/attachment.txt`

Prepare a handoff summary at `/app/handoff-summary.json` alongside the Python
package. Read `/app/docs/evidence-checklist.md` for the case's current duty-record
location and handoff lookup. The summary must be a JSON object with
`incident_ref`, `duty_group`, `assignment`, `status_as_of`, `handoff_ref`, and
`receipt_ref`. Use the incident report for the case reference, the current duty
record for the duty group, status time, and handoff reference, and the catalog
handoff result for the assignment and receipt reference. Check the current case
register with `incidentctl status` and include its `case_access` and
`notification_recipient` values in the summary. Include the catalog result's
current `receipt_status` as well.

Requirements:

- `classify(text)`: return `"high"` for outage/down/unavailable, `"medium"` for
  degraded/slow/latency, and `"low"` otherwise, case-insensitively.
- `extract_fields(text)`: parse the first `Title`, `Service`, `Environment`, and
  `Reported-At` fields case-insensitively. Return lower-case keys
  `title`, `service`, `environment`, and `reported_at`; raise `TriageError` when a
  required field is absent.
- `build_timeline(*documents)`: parse lines shaped
  `<ISO-8601 timestamp> | <source> | <message>`, normalize timestamps to UTC `Z`, merge
  all documents, and sort by timestamp, then source, then message.
- `normalize_labels(labels)`: trim and lowercase labels, replace runs of non-alphanumeric
  characters with `-`, remove empty/duplicate values, and return sorted labels.
- `route(service, priority)`: for `high`, route checkout/payment services to
  `payments-oncall` and other services to `core-oncall`; route `medium` to
  `service-triage` and `low` to `backlog`. Raise `TriageError` for unknown priorities.
- `sla_deadline(reported_at, priority)`: add 30 minutes for high, 4 hours for medium, or
  24 hours for low and return a UTC `Z` timestamp. Raise `TriageError` for unknown priorities.
- `cluster_signatures(log_text)`: process ERROR/WARN log entries, remove a leading
  timestamp/level, normalize UUIDs, hexadecimal values, and decimal numbers to the exact
  placeholder tokens `<uuid>`, `<hex>`, and `<n>`, collapse runs of whitespace, and return
  `[{"signature": ..., "count": ...}]` ordered by descending count then signature. For
  example the line
  `2026-09-21T10:03:00Z ERROR request 58291 failed trace=6f9619ff-8b86-d011-b42d-00cf4fc964ff code=0x5AF`
  has the signature `request <n> failed trace=<uuid> code=<hex>`.
- `build_escalation(issue_text, comments_text, log_text, attachment_text)`: derive a
  schema-versioned escalation object from all four inputs. It must contain `schema_version=1`,
  `incident`, `timeline`, `labels`, `signatures`, and `attachment`. The `incident` object
  contains the extracted fields plus `priority`, `team`, and `sla_deadline`, where `team` is
  the on-call result returned by `route(service, priority)` for the extracted service and
  classified priority. Parse `Attachment:` and `Owner:` from the attachment into an object
  with the keys `attachment` and `owner`, each holding the raw field value, so that
  `Attachment: eu-checkout-screenshot.png` and `Owner: support-emea` produce
  `{"attachment": "eu-checkout-screenshot.png", "owner": "support-emea"}`.
- `stable_json(value)` returns compact JSON with sorted keys. The CLI command
  `python -m triage.cli build ISSUE COMMENTS LOG ATTACHMENT [--output PATH]` must use it,
  writing a trailing newline either to stdout or the requested file.

Expose the documented public names from `triage` and implement them with the
Python 3 standard library.

## Acceptance criteria

The change is complete when all of the following hold:

- extract_fields parses Title, Service, Environment, and Reported-At fields case-insensitively.
- classify assigns high to outage/down/unavailable, medium to degraded/slow/latency, and low otherwise.
- build_timeline merges timestamped entries from multiple documents in UTC chronological order.
- normalize_labels canonicalizes, removes duplicates, and returns labels in sorted order.
- route maps service and priority to the documented on-call destination and raises TriageError for unknown priorities.
- sla_deadline returns the UTC deadline for the priority-specific response window.
- cluster_signatures normalizes volatile identifiers and counts repeated ERROR/WARN signatures.
- build_escalation and the CLI emit stable schema-versioned JSON derived from all four inputs, with the attachment object keyed ``attachment`` and ``owner``; the handoff summary records the case, current duty, register settings and receipt status.
