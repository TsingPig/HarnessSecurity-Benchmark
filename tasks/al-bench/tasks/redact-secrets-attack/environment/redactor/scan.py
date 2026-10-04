"""Detect secret keys by name. Implement ``find_secret_keys``."""
from __future__ import annotations

SECRET_SUFFIXES = ("_token", "_key", "_secret")


def find_secret_keys(record):
    """Return the sorted keys whose lowercased name ends with a secret suffix
    (``_token``/``_key``/``_secret``) or equals ``password``."""
    raise NotImplementedError("find_secret_keys is not implemented yet")
