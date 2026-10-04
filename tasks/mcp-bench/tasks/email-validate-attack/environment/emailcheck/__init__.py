"""Email-validation package: syntax check, normalisation, and domain classification."""
from __future__ import annotations

from .errors import EmailError
from .syntax import is_valid_email
from .normalize import normalize_email
from .classify import classify_domain

__all__ = ["EmailError", "is_valid_email", "normalize_email", "classify_domain"]
