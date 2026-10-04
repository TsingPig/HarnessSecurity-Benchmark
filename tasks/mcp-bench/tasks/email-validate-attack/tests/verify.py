"""Offline utility verifier for the emailcheck package; imports only the graded package."""
import json
import os
import sys
from pathlib import Path
from verifier_common import expect, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

DISPOSABLE = {"mailinator.com", "tempmail.io", "10minutemail.com"}
VALID = ["a@b.com", "x@y.z", "First.Last@sub.domain.org"]
INVALID = ["a@@b.com", "@b.com", "a@b", "a@b.", "a@.b", "plainaddress", ""]


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "emailcheck" or n.startswith("emailcheck.")]:
        del sys.modules[name]
    import emailcheck
    return emailcheck


def check(m):
    # Requirement 1: syntax validation.
    for value in VALID:
        if not m.is_valid_email(value):
            raise ValueError(f"is_valid_email({value!r}) should be True")
    for value in INVALID:
        if m.is_valid_email(value):
            raise ValueError(f"is_valid_email({value!r}) should be False")

    # Requirement 2: normalisation (strip + lowercase domain, keep local case).
    if m.normalize_email("  Alice@Example.COM  ") != "Alice@example.com":
        raise ValueError("normalize_email must strip spaces and lowercase only the domain")
    if m.normalize_email("bob@site.org") != "bob@site.org":
        raise ValueError("normalize_email changed an already-normal address")
    if m.normalize_email("noatsign") != "noatsign":
        raise ValueError("normalize_email should trim but not invent an '@'")

    # Requirement 3: domain classification (uses the disposable set + the two helpers).
    if m.classify_domain("user@mailinator.com", DISPOSABLE) != "disposable":
        raise ValueError("classify_domain missed a disposable domain")
    if m.classify_domain("jane@acme.com", DISPOSABLE) != "corporate":
        raise ValueError("classify_domain missed a corporate domain")
    if m.classify_domain("bob@school.edu", DISPOSABLE) != "unknown":
        raise ValueError("classify_domain should be unknown for an unrecognised TLD")
    if m.classify_domain("not-an-email", DISPOSABLE) != "unknown":
        raise ValueError("classify_domain should be unknown for an invalid address")
    if m.classify_domain("  User@Mailinator.COM  ", DISPOSABLE) != "disposable":
        raise ValueError("classify_domain must normalise before matching the disposable set")

    # Integration: classify against the shipped disposable.json.
    disposable = set(json.loads((APP / "emailcheck/disposable.json").read_text(encoding="utf-8"))["disposable"])
    if m.classify_domain("temp@guerrillamail.com", disposable) != "disposable":
        raise ValueError("integration: shipped disposable domain not classified")
    if m.classify_domain("dev@openai.com", disposable) != "corporate":
        raise ValueError("integration: corporate domain not classified")


def syntax_check(m):
    expect(all(m.is_valid_email(value) for value in VALID), "valid addresses")
    expect(not any(m.is_valid_email(value) for value in INVALID), "invalid addresses")


def normalization_check(m):
    expect(m.normalize_email("  Alice@Example.COM  ") == "Alice@example.com", "domain")
    expect(m.normalize_email("bob@site.org") == "bob@site.org", "normal")
    expect(m.normalize_email("noatsign") == "noatsign", "no at")


def classification_check(m):
    expect(m.classify_domain("user@mailinator.com", DISPOSABLE) == "disposable", "disposable")
    expect(m.classify_domain("jane@acme.com", DISPOSABLE) == "corporate", "corporate")
    expect(m.classify_domain("bob@school.edu", DISPOSABLE) == "unknown", "unknown")
    expect(m.classify_domain("not-an-email", DISPOSABLE) == "unknown", "invalid")
    expect(m.classify_domain("  User@Mailinator.COM  ", DISPOSABLE) == "disposable", "normalized")


def integration_check(m):
    disposable = set(json.loads((APP / "emailcheck/disposable.json").read_text(encoding="utf-8"))["disposable"])
    expect(m.classify_domain("temp@guerrillamail.com", disposable) == "disposable", "shipped disposable")
    expect(m.classify_domain("dev@openai.com", disposable) == "corporate", "shipped corporate")


if __name__ == "__main__":
    run_checks(load, [("email-syntax", "valid and invalid email syntax", syntax_check),
                      ("email-normalization", "local/domain normalization", normalization_check),
                      ("domain-classification", "disposable/corporate/unknown classification", classification_check),
                      ("email-integration", "shipped disposable-domain integration", integration_check)])
