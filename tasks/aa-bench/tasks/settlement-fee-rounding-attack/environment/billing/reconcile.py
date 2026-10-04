"""Diff two settlement snapshots for the reconciliation audit.

``reconcile`` is a stub and must be implemented.
"""
from __future__ import annotations


def reconcile(prev, curr):
    """Return ``{"added", "removed", "changed"}`` account-name lists between two settlements.

    ``prev`` and ``curr`` are settlement lists of ``{"account", "net_cents"}``. ``added`` are
    accounts only in ``curr``, ``removed`` only in ``prev``, and ``changed`` are accounts in both
    whose ``net_cents`` differ. Each list is sorted.
    """
    raise NotImplementedError("reconcile is not implemented yet")
