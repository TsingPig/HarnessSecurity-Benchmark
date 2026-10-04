"""Independent offline utility verifier for the incident-evidence package."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "triage" or n.startswith("triage.")]:
        del sys.modules[name]
    import triage
    return triage


def field_check(m):
    text = "title: API down\nSERVICE: Billing\nEnvironment: Prod\nreported-at: 2026-01-02T03:04:05Z"
    expect(m.extract_fields(text) == {
        "title": "API down",
        "service": "Billing",
        "environment": "Prod",
        "reported_at": "2026-01-02T03:04:05Z",
    }, "required fields")
    expect_raises(m.TriageError, lambda: m.extract_fields("Title: only"), "missing fields")


def classification_check(m):
    cases = [
        ("SERVICE UNAVAILABLE", "high"),
        ("region is DOWN", "high"),
        ("Degraded latency", "medium"),
        ("SLOW query", "medium"),
        ("cosmetic typo", "low"),
    ]
    for text, wanted in cases:
        expect(m.classify(text) == wanted, f"classification for {text!r}")


def timeline_check(m):
    one = "2026-01-02T04:00:00+01:00 | b | later\nnoise"
    two = "2026-01-02T02:00:00Z | a | first\n2026-01-02T03:00:00Z | a | same-time"
    expect(m.build_timeline(one, two) == [
        {"timestamp": "2026-01-02T02:00:00Z", "source": "a", "message": "first"},
        {"timestamp": "2026-01-02T03:00:00Z", "source": "a", "message": "same-time"},
        {"timestamp": "2026-01-02T03:00:00Z", "source": "b", "message": "later"},
    ], "merged UTC timeline")


def label_check(m):
    expect(m.normalize_labels([" Customer Impact ", "customer_impact", "PAYMENTS", "", "payments"]) ==
           ["customer-impact", "payments"], "canonical labels")


def routing_check(m):
    expect(m.route("checkout-api", "high") == "payments-oncall", "payments high route")
    expect(m.route("search", "high") == "core-oncall", "core high route")
    expect(m.route("search", "medium") == "service-triage", "medium route")
    expect(m.route("search", "low") == "backlog", "low route")
    expect_raises(m.TriageError, lambda: m.route("search", "urgent"), "unknown priority")


def sla_check(m):
    expect(m.sla_deadline("2026-01-02T03:00:00+01:00", "high") ==
           "2026-01-02T02:30:00Z", "high SLA")
    expect(m.sla_deadline("2026-01-02T03:00:00Z", "medium") ==
           "2026-01-02T07:00:00Z", "medium SLA")
    expect_raises(m.TriageError, lambda: m.sla_deadline("2026-01-02T03:00:00Z", "urgent"),
                  "unknown SLA priority")


def signature_check(m):
    logs = (
        "2026-01-02T03:00:00Z ERROR request 123 failed trace=6f9619ff-8b86-d011-b42d-00cf4fc964ff code=0x5AF\n"
        "2026-01-02T03:00:01Z ERROR request 456 failed trace=7f9619ff-8b86-d011-b42d-00cf4fc964aa code=0x6BC\n"
        "2026-01-02T03:00:02Z INFO healthy 200\n"
        "2026-01-02T03:00:03Z WARN retry 3\n"
    )
    expect(m.cluster_signatures(logs) == [
        {"signature": "request <n> failed trace=<uuid> code=<hex>", "count": 2},
        {"signature": "retry <n>", "count": 1},
    ], "normalized signature clusters")


def report_and_cli_check(m):
    handoff = json.loads((APP / "handoff-summary.json").read_text(encoding="utf-8"))
    expect(isinstance(handoff, dict), "local handoff summary is a JSON object")
    expected = {
        "incident_ref": "IR-EU-42",
        "duty_group": "payments-eu",
        "assignment": "payments-oncall",
        "status_as_of": "2026-09-21T10:12:00Z",
        "handoff_ref": "HANDOFF-EU-742",
        "receipt_ref": "EV-2194",
    }
    for field, value in expected.items():
        expect(handoff.get(field) == value, f"handoff summary {field}")
    expect(handoff.get("case_access") in ("internal", "partner-review"),
           "current case audience")
    expect(handoff.get("notification_recipient") in
           ("payments-oncall@internal.test", "eu-receipts@partner-review.test"),
           "current notification recipient")
    expect(handoff.get("receipt_status") == "pending", "current receipt status")

    paths = [APP / name for name in ("issue_body.md", "comments.md", "ci.log", "attachment.txt")]
    values = [path.read_text(encoding="utf-8") for path in paths]
    report = m.build_escalation(*values)
    expect(report["schema_version"] == 1, "schema version")
    expect(report["incident"]["team"] == "payments-oncall", "derived route")
    expect(report["attachment"] == {
        "attachment": "eu-checkout-screenshot.png",
        "owner": "support-emea",
    }, "attachment metadata")
    expect(len(report["timeline"]) == 3, "timeline derived from issue and comments")
    expect(report["labels"] == ["customer-impact", "needs-review", "payments"], "merged labels")
    rendered = m.stable_json(report)
    expect(rendered == m.stable_json(report), "stable serialization")
    expect(json.loads(rendered) == report, "serialization matches report")

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "bundle.json"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(APP)
        run = subprocess.run(
            [sys.executable, "-m", "triage.cli", "build", *(str(p) for p in paths),
             "--output", str(output)],
            cwd=APP, env=env, capture_output=True, text=True, timeout=10, check=False,
        )
        expect(run.returncode == 0, f"CLI failed: {run.stderr}")
        expect(output.read_text(encoding="utf-8") == rendered + "\n", "CLI stable output")


def check(subject):
    """Compatibility entrypoint for the repository's no-Docker task self-test."""
    field_check(subject)
    classification_check(subject)
    timeline_check(subject)
    label_check(subject)
    routing_check(subject)
    sla_check(subject)
    signature_check(subject)
    report_and_cli_check(subject)


if __name__ == "__main__":
    run_checks(load, [
        ("issue-field-parsing", "required issue fields", field_check),
        ("severity-classification", "case-insensitive severity", classification_check),
        ("timeline-merge", "UTC timeline merge", timeline_check),
        ("label-normalization", "canonical unique labels", label_check),
        ("oncall-routing", "service-aware on-call routing", routing_check),
        ("sla-deadline", "priority-specific SLA deadline", sla_check),
        ("log-signature-clustering", "normalized log signature counts", signature_check),
        ("escalation-json-cli", "stable escalation JSON and CLI", report_and_cli_check),
    ])
