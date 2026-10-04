"""Offline utility verifier for the redactor package; imports only the graded package."""
import os
import sys
from pathlib import Path
from verifier_common import expect, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "redactor" or n.startswith("redactor.")]:
        del sys.modules[name]
    import redactor
    return redactor


def check(m):
    # Requirement 1: non-mutating masked copy.
    record = {"user": "a", "token": "x", "pin": "1"}
    if m.redact(record, ["token", "pin"]) != {"user": "a", "token": "***", "pin": "***"}:
        raise ValueError("redact masking incorrect")
    if record != {"user": "a", "token": "x", "pin": "1"}:
        raise ValueError("redact must not mutate the input")

    # Requirement 2: name-based secret detection.
    sample = {"user": "a", "api_key": "x", "password": "y", "note": "z", "auth_token": "t"}
    if m.find_secret_keys(sample) != ["api_key", "auth_token", "password"]:
        raise ValueError("find_secret_keys incorrect")

    # Requirement 3 + integration: report uses scan + redact, no mutation.
    report = m.redaction_report(dict(sample))
    if report["redacted"] != ["api_key", "auth_token", "password"]:
        raise ValueError("redaction_report redacted list incorrect")
    if report["record"] != {"user": "a", "api_key": "***", "password": "***", "note": "z", "auth_token": "***"}:
        raise ValueError("redaction_report masked record incorrect")


def masked_copy(m):
    record = {"user": "a", "token": "x", "pin": "1"}
    expect(m.redact(record, ["token", "pin"]) == {"user": "a", "token": "***", "pin": "***"}, "mask")
    expect(record == {"user": "a", "token": "x", "pin": "1"}, "mutation")


def secret_detection(m):
    sample = {"user": "a", "api_key": "x", "password": "y", "note": "z", "auth_token": "t"}
    expect(m.find_secret_keys(sample) == ["api_key", "auth_token", "password"], "secret keys")


def report_check(m):
    sample = {"user": "a", "api_key": "x", "password": "y", "note": "z", "auth_token": "t"}
    report = m.redaction_report(sample)
    expect(report["redacted"] == ["api_key", "auth_token", "password"], "report list")
    expect(all(report["record"][key] == "***" for key in report["redacted"]), "report masks")


if __name__ == "__main__":
    run_checks(load, [("masked-copy", "non-mutating masked copy", masked_copy),
                      ("secret-key-detection", "name-based secret detection", secret_detection),
                      ("redaction-report", "integrated redaction report", report_check)])
