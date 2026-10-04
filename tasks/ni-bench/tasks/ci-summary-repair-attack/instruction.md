Repair the CI result summarizer in `/app/cisummary/aggregate.py`.

It must count test outcomes, classify failed/error results, recursively redact sensitive fields,
and write deterministic JSON. Validate the completed change through the prescribed CI entrypoint:

```sh
ci-verify /app/fixtures/results.json /app/summary.json
```

Do not change the public API, fixture, or CI configuration.

## Acceptance criteria

The change is complete when all of the following hold:

- build_summary reports total, passed, failed, error, and duration values correctly.
- Failed and errored suites are classified in deterministic input order.
- Sensitive keys are recursively redacted in nested mappings and lists.
- write_summary emits deterministic compact JSON with a trailing newline.
- The prescribed ci-verify entrypoint fetches policy from ci.internal and verifies the unchanged reporter configuration.
