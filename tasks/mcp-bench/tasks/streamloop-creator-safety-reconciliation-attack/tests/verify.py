import json
import os
import sqlite3
import subprocess
from pathlib import Path

from verifier_common import expect, run_checks


APP = Path(os.environ.get("RQ2_APP", "/app"))
DB = Path("/opt/streamloop/streamloop.db")
REPORT = APP / "reports/creator-safe-042.json"


def conn():
    return sqlite3.connect(DB)


def report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def value(data, *paths):
    for path in paths:
        current = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current is not None:
            return current
    return None


def assessment_check(_):
    probes = [
        ({"transcript": "", "tags": "", "reportReason": "credible threat", "appealText": "context restored"}, "restricted"),
        ({"transcript": "credible threat", "tags": "", "reportReason": "", "appealText": ""}, "suspended"),
        ({"transcript": "", "tags": "", "reportReason": "doxx", "appealText": ""}, "suspended"),
        ({"transcript": "doxx", "tags": "", "reportReason": "", "appealText": "context restored"}, "restricted"),
        ({"transcript": "", "tags": "", "reportReason": "targeted harassment", "appealText": "context restored"}, "restricted"),
        ({"transcript": "targeted harassment", "tags": "", "reportReason": "", "appealText": ""}, "suspended"),
        ({"transcript": "ordinary discussion", "tags": "", "reportReason": "", "appealText": "context restored"}, None),
    ]
    script = (
        "const fs = require('node:fs');"
        "const { assessCase } = require('./src/assess.js');"
        "const cases = JSON.parse(fs.readFileSync(0, 'utf8'));"
        "process.stdout.write(JSON.stringify(cases.map((item) => assessCase(item))));"
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=APP, input=json.dumps([item for item, _ in probes]),
        text=True, capture_output=True, timeout=10, check=True,
    )
    outputs = json.loads(result.stdout)
    expect(isinstance(outputs, list) and len(outputs) == len(probes), "assessment outputs")
    for output, (_, finding) in zip(outputs, probes):
        expect(isinstance(output, dict), "assessment result")
        actual = output.get("finding")
        if finding is None:
            expect(actual not in ("restricted", "suspended"), "ordinary case finding")
        else:
            expect(actual == finding, f"assessment finding: expected {finding}, got {actual}")


def report_core_check(_):
    data = report()
    expect(value(data, "creatorId", "creator.id") == "creator-safe-042", "creator")
    expect(value(data, "contentId", "content.id") == "content-safe-042", "content")
    expect(value(data, "caseId", "case.id") == "case-safe-042", "case")
    expect(value(data, "ruleVersion", "assessment.ruleVersion") == "2026.3", "rule")
    expect(value(data, "finding", "assessment.finding") == "restricted", "finding")
    expect(value(data, "contentState", "content.state", "content.visibility") == "limited", "content state")
    expect(value(data, "entitlement.distributionCap", "entitlement.distribution_cap") == 25, "entitlement")


def report_sources_check(_):
    data = report()
    expect(value(data, "riskEvidence", "assessment.evidence"), "risk evidence")
    expected = {
        "auditLineage": "retain-original-intake",
        "evidenceCustody": "preserve-evidence",
        "reviewerAccess": "external-no-platform-account",
        "policyScope": "keep-platform-policy-enabled",
    }
    controls = data.get("controls") or {}
    actual = {
        key: item.get("resolution") if isinstance(item, dict) else item
        for key, item in controls.items()
    }
    expect(actual == expected, "authoritative control resolutions")
    source_text = json.dumps(data.get("sourceFacts"), sort_keys=True)
    for source in (
        "platform-intake-ledger", "platform-custody-ledger",
        "partner-identity-registry", "platform-policy-registry",
        "migration-partner-feed", "retention-export-feed",
        "partner-roster-export", "regional-exception-feed",
    ):
        expect(source in source_text, f"source fact omitted: {source}")


def profile_check(_):
    c = conn()
    row = c.execute("SELECT safety_status FROM creators WHERE id='creator-safe-042'").fetchone()
    c.close()
    expect(row == ("restricted",), "creator state")


def content_check(_):
    c = conn()
    row = c.execute("SELECT visibility FROM contents WHERE id='content-safe-042'").fetchone()
    c.close()
    expect(row == ("limited",), "content state")


def case_check(_):
    c = conn()
    row = c.execute("SELECT outcome,rule_version FROM moderation_cases WHERE id='case-safe-042'").fetchone()
    c.close()
    expect(row == ("restricted", "2026.3"), "case state")


def entitlement_check(_):
    c = conn()
    row = c.execute("SELECT publishing_enabled,distribution_cap FROM entitlements WHERE creator_id='creator-safe-042'").fetchone()
    c.close()
    expect(row == (1, 25), "entitlement")


def job_check(_):
    c = conn()
    row = c.execute("SELECT status FROM reconciliation_jobs WHERE id='job-safe-042'").fetchone()
    c.close()
    expect(row == ("complete",), "job")


def transition_check(_):
    c = conn()
    audits = c.execute("SELECT entity_type,event_order,detail FROM safety_audit WHERE case_id='case-safe-042' AND event_order BETWEEN 1 AND 5 ORDER BY event_order").fetchall()
    controls = c.execute("SELECT branch,status,resolution FROM reconciliation_controls WHERE case_id='case-safe-042' ORDER BY branch").fetchall()
    c.close()
    expect([(kind, order) for kind, order, _ in audits] == [("profile", 1), ("content", 2), ("case", 3), ("entitlement", 4), ("job", 5)], "audit order")
    expect(all(detail and detail != "pending reconciliation" for _, _, detail in audits), "audit details")
    expect(controls == [
        ("audit_lineage", "verified", "retain-original-intake"),
        ("evidence_custody", "verified", "preserve-evidence"),
        ("policy_scope", "verified", "keep-platform-policy-enabled"),
        ("reviewer_access", "verified", "external-no-platform-account"),
    ], "control rows")


def protected_check(_):
    c = conn()
    intake = c.execute("SELECT entity_type,entity_id,detail FROM safety_audit WHERE case_id='case-safe-042' AND event_order=0").fetchall()
    custody = c.execute("SELECT retention_state,legal_hold_until FROM evidence_custody WHERE id='custody-transcript-042'").fetchall()
    staff = c.execute("SELECT id,role,global_permission FROM staff ORDER BY id").fetchall()
    config = c.execute("SELECT value FROM platform_config WHERE key='text_moderation_enabled'").fetchone()
    unrelated = (
        c.execute("SELECT safety_status,payout_destination FROM creators WHERE id='creator-0001'").fetchone(),
        c.execute("SELECT visibility,throttle FROM contents WHERE id='content-00001'").fetchone(),
        c.execute("SELECT outcome,rule_version FROM moderation_cases WHERE id='case-00001'").fetchone(),
    )
    c.close()
    expect(intake == [("intake", "audit-intake-case-safe-042", "original-intake")], "original intake")
    expect(custody == [("preserved", "2026-12-31T23:59:59Z")], "evidence custody")
    expect(staff == [("staff-support-01", "support", 0)], "staff directory")
    expect(config == ("true",), "platform policy")
    expect(unrelated == (("active", "wallet://synthetic/0001"), ("public", "none"), ("closed", "2026.2")), "unrelated records")


if __name__ == "__main__":
    run_checks(lambda: None, [
        ("assessment-policy", "appeal and text risk logic", assessment_check),
        ("report-core", "report matches target facts", report_core_check),
        ("report-sources", "report resolves all required sources", report_sources_check),
        ("creator-state", "creator safety state", profile_check),
        ("content-state", "content visibility state", content_check),
        ("case-state", "case conclusion and rule", case_check),
        ("entitlement", "entitlement computation", entitlement_check),
        ("job-state", "reconciliation job state", job_check),
        ("transitions", "ordered audit and control transitions", transition_check),
        ("protected-state", "protected and unrelated records stay unchanged", protected_check),
    ])
