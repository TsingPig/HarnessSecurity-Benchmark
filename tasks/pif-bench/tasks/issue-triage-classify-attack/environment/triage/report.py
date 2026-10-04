"""Escalation bundle construction and stable serialization."""
from __future__ import annotations


def build_escalation(issue_text, comments_text, log_text, attachment_text):
    """Build the schema-versioned escalation object."""
    raise NotImplementedError("build_escalation is not implemented")


def stable_json(value):
    """Serialize a value as compact JSON with stable key ordering."""
    raise NotImplementedError("stable_json is not implemented")
