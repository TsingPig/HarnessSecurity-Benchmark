"""Token helpers shared by the parser (provided; do not rewrite)."""
from __future__ import annotations


def is_long(token):
    """Return ``True`` if ``token`` is a long option (``--name`` or ``--name=value``)."""
    return token.startswith("--") and len(token) > 2


def split_option(body):
    """Split the text after ``--`` on the first ``=``.

    Return ``(key, value)`` where ``value`` is everything after the first ``=`` (which may be an
    empty string), or ``(body, None)`` when there is no ``=`` (a bare flag).
    """
    if "=" in body:
        key, value = body.split("=", 1)
        return key, value
    return body, None
