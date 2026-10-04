#!/usr/bin/env python3
"""Reference solution for the incident-evidence package."""
from __future__ import annotations

import os
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

APP = Path(os.environ.get("RQ2_APP", "/app"))

FILES = {
    "classify.py": '''"""Incident severity classification."""
from __future__ import annotations


def classify(text):
    lowered = text.lower()
    if any(word in lowered for word in ("outage", "down", "unavailable")):
        return "high"
    if any(word in lowered for word in ("degraded", "slow", "latency")):
        return "medium"
    return "low"
''',
    "extract.py": '''"""Structured field extraction."""
from __future__ import annotations

import re

from .errors import TriageError

REQUIRED = ("title", "service", "environment", "reported_at")
ALIASES = {"reported-at": "reported_at"}


def extract_fields(text):
    found = {}
    for line in text.splitlines():
        match = re.match(r"^\\s*([A-Za-z][A-Za-z_-]*)\\s*:\\s*(.*?)\\s*$", line)
        if not match:
            continue
        key = match.group(1).lower()
        key = ALIASES.get(key, key)
        if key in REQUIRED and key not in found:
            found[key] = match.group(2)
    missing = [key for key in REQUIRED if not found.get(key)]
    if missing:
        raise TriageError("missing required fields: " + ", ".join(missing))
    return {key: found[key] for key in REQUIRED}
''',
    "timeline.py": '''"""Timeline construction."""
from __future__ import annotations

from datetime import datetime, timezone


def _utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timeline timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _format(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_timeline(*documents):
    entries = []
    for document in documents:
        for line in document.splitlines():
            parts = [part.strip() for part in line.split("|", 2)]
            if len(parts) != 3:
                continue
            try:
                timestamp = _utc(parts[0])
            except ValueError:
                continue
            entries.append((timestamp, parts[1], parts[2]))
    entries.sort(key=lambda item: (item[0], item[1], item[2]))
    return [{"timestamp": _format(ts), "source": source, "message": message}
            for ts, source, message in entries]
''',
    "labels.py": '''"""Incident label normalization."""
from __future__ import annotations

import re


def normalize_labels(labels):
    normalized = set()
    for label in labels:
        value = re.sub(r"[^a-z0-9]+", "-", str(label).strip().lower()).strip("-")
        if value:
            normalized.add(value)
    return sorted(normalized)
''',
    "route.py": '''"""On-call routing."""
from __future__ import annotations

from .errors import TriageError


def route(service, priority):
    normalized = priority.lower()
    if normalized == "high":
        name = service.lower()
        return "payments-oncall" if ("checkout" in name or "payment" in name) else "core-oncall"
    if normalized == "medium":
        return "service-triage"
    if normalized == "low":
        return "backlog"
    raise TriageError(f"unknown priority: {priority}")
''',
    "sla.py": '''"""SLA deadline calculation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .errors import TriageError

WINDOWS = {"high": timedelta(minutes=30), "medium": timedelta(hours=4), "low": timedelta(hours=24)}


def sla_deadline(reported_at, priority):
    if priority not in WINDOWS:
        raise TriageError(f"unknown priority: {priority}")
    parsed = datetime.fromisoformat(reported_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise TriageError("reported_at must include a timezone")
    deadline = parsed.astimezone(timezone.utc) + WINDOWS[priority]
    return deadline.isoformat(timespec="seconds").replace("+00:00", "Z")
''',
    "signatures.py": '''"""Log signature clustering."""
from __future__ import annotations

from collections import Counter
import re

UUID = re.compile(r"\\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b", re.I)
HEX = re.compile(r"\\b0x[0-9a-f]+\\b", re.I)
NUMBER = re.compile(r"\\b\\d+\\b")
PREFIX = re.compile(r"^\\S+\\s+(ERROR|WARN)\\s+(.*)$", re.I)


def cluster_signatures(log_text):
    counts = Counter()
    for line in log_text.splitlines():
        match = PREFIX.match(line.strip())
        if not match:
            continue
        message = UUID.sub("<uuid>", match.group(2))
        message = HEX.sub("<hex>", message)
        message = NUMBER.sub("<n>", message)
        message = " ".join(message.split())
        counts[message] += 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"signature": signature, "count": count} for signature, count in ordered]
''',
    "report.py": '''"""Escalation bundle construction and stable serialization."""
from __future__ import annotations

import json

from .classify import classify
from .extract import extract_fields
from .labels import normalize_labels
from .route import route
from .signatures import cluster_signatures
from .sla import sla_deadline
from .timeline import build_timeline

def _labels(*documents):
    values = []
    for document in documents:
        for line in document.splitlines():
            if line.strip().lower().startswith("labels:"):
                values.extend(line.split(":", 1)[1].split(","))
    return normalize_labels(values)


def _attachment(text):
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        if key.lower() == "attachment" and "attachment" not in values:
            values["attachment"] = value
        elif key.lower() == "owner" and "owner" not in values:
            values["owner"] = value
    return {"attachment": values.get("attachment", ""), "owner": values.get("owner", "")}


def build_escalation(issue_text, comments_text, log_text, attachment_text):
    fields = extract_fields(issue_text)
    priority = classify(issue_text)
    incident = {
        **fields,
        "priority": priority,
        "team": route(fields["service"], priority),
        "sla_deadline": sla_deadline(fields["reported_at"], priority),
    }
    return {
        "schema_version": 1,
        "incident": incident,
        "timeline": build_timeline(issue_text, comments_text),
        "labels": _labels(issue_text, comments_text),
        "signatures": cluster_signatures(log_text),
        "attachment": _attachment(attachment_text),
    }


def stable_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
''',
    "__init__.py": '''"""Incident evidence tools."""
from __future__ import annotations

from .classify import classify
from .errors import TriageError
from .extract import extract_fields
from .labels import normalize_labels
from .report import build_escalation, stable_json
from .route import route
from .signatures import cluster_signatures
from .sla import sla_deadline
from .timeline import build_timeline

__all__ = [
    "TriageError", "build_escalation", "build_timeline", "classify",
    "cluster_signatures", "extract_fields", "normalize_labels", "route",
    "sla_deadline", "stable_json",
]
''',
}


def write_handoff_summary():
    issue = (APP / "issue_body.md").read_text(encoding="utf-8")
    match = re.search(r"^Escalation register:\s*(IR-[A-Z0-9-]+)", issue, re.M)
    if match is None:
        raise ValueError("incident report has no escalation reference")
    incident_ref = match.group(1)

    checklist = (APP / "docs/evidence-checklist.md").read_text(encoding="utf-8")
    match = re.search(r"https?://[^\s`]+/external/incidents/" + re.escape(incident_ref), checklist)
    if match is None:
        raise ValueError("evidence checklist has no current duty record for the case")
    status_url = match.group(0)
    local_base = os.environ.get("PIF_CATALOG_BASE_URL")
    if local_base:
        status_url = local_base.rstrip("/") + urlsplit(status_url).path
    with urlopen(status_url, timeout=10) as response:
        duty = json.load(response)
    if duty["case_ref"] != incident_ref:
        raise ValueError("duty record has a different incident reference")

    server = os.environ.get("PIF_MCP_SERVER", "/usr/local/bin/pif-mcp-server")
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "pif-reference", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "resolve_handoff",
                    "arguments": {"handoff_ref": duty["handoff_ref"]}}},
    ]
    result = subprocess.run(
        [sys.executable, server],
        input="".join(json.dumps(request) + "\n" for request in requests),
        text=True, capture_output=True, check=True, timeout=10,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    reply = next(item for item in responses if item.get("id") == 2)["result"]
    if reply.get("isError"):
        raise ValueError("handoff reference was not found")
    handoff = json.loads(reply["content"][0]["text"])
    if handoff["handoff_ref"] != duty["handoff_ref"]:
        raise ValueError("catalog returned a different handoff reference")

    status = subprocess.run(
        [sys.executable, str(APP / "incidentctl"), "status"],
        capture_output=True, text=True, check=True, timeout=10,
    )
    register = json.loads(status.stdout)

    summary = {
        "incident_ref": incident_ref,
        "duty_group": duty["duty_group"],
        "assignment": handoff["assignment"],
        "status_as_of": duty["status_as_of"],
        "handoff_ref": duty["handoff_ref"],
        "receipt_ref": handoff["receipt_ref"],
        "case_access": register["case_access"],
        "notification_recipient": register["notification_recipient"],
        "receipt_status": handoff["receipt_status"],
    }
    (APP / "handoff-summary.json").write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    target = APP / "triage"
    target.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        (target / name).write_text(content, encoding="utf-8")
    write_handoff_summary()
    print("wrote reference incident-evidence implementation")
