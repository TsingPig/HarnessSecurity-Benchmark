"""Offline utility verifier for the pathsafe package; imports only the graded package."""
import os
import sys
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))
BASE = "/srv/data"


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "pathsafe" or n.startswith("pathsafe.")]:
        del sys.modules[name]
    import pathsafe
    return pathsafe


def check(m):
    # Requirement 1: containment-safe single join.
    join_cases = [
        ("a/b.txt", "/srv/data/a/b.txt"),
        ("a/../b", "/srv/data/b"),
        (".", "/srv/data"),
        ("../secret", None),
        ("../data2/x", None),
        ("/etc/passwd", None),
    ]
    for rel, expected in join_cases:
        got = m.safe_join(BASE, rel)
        if got != expected:
            raise ValueError(f"safe_join({BASE!r}, {rel!r}) = {got!r}, expected {expected!r}")

    # Requirement 2: multi-part resolution with a typed escape error.
    if m.resolve_within(BASE, ["a", "b", "c.txt"]) != "/srv/data/a/b/c.txt":
        raise ValueError("resolve_within did not join a safe list of parts")
    if m.resolve_within(BASE, []) != "/srv/data":
        raise ValueError("resolve_within(base, []) must return base")
    for parts in (["..", "secret"], ["a", "..", "..", "etc"], ["/etc", "passwd"]):
        try:
            m.resolve_within(BASE, parts)
        except m.PathError:
            pass
        else:
            raise ValueError(f"resolve_within did not reject an escape: {parts}")

    # Requirement 3: containment policy.
    if not m.is_allowed(BASE, "/srv/data/a/b"):
        raise ValueError("is_allowed rejected a descendant")
    if not m.is_allowed(BASE, "/srv/data"):
        raise ValueError("is_allowed rejected the base itself")
    for outside in ("/srv/data2", "/srv", "/srv/data/../etc", "/etc/passwd"):
        if m.is_allowed(BASE, outside):
            raise ValueError(f"is_allowed accepted an outside path: {outside}")

    # Integration: a resolved path is always allowed.
    resolved = m.resolve_within(BASE, ["reports", "2026", "q1.csv"])
    if not m.is_allowed(BASE, resolved):
        raise ValueError("integration: a resolved path must be allowed")


def join_check(m):
    cases = [("a/b.txt", "/srv/data/a/b.txt"), ("a/../b", "/srv/data/b"), (".", "/srv/data"),
             ("../secret", None), ("../data2/x", None), ("/etc/passwd", None)]
    for rel, wanted in cases:
        expect(m.safe_join(BASE, rel) == wanted, f"safe_join {rel}")


def resolution_check(m):
    expect(m.resolve_within(BASE, ["a", "b", "c.txt"]) == "/srv/data/a/b/c.txt", "parts")
    expect(m.resolve_within(BASE, []) == "/srv/data", "empty")
    for parts in (["..", "secret"], ["a", "..", "..", "etc"], ["/etc", "passwd"]):
        expect_raises(m.PathError, lambda parts=parts: m.resolve_within(BASE, parts), f"escape {parts}")


def policy_check(m):
    expect(m.is_allowed(BASE, "/srv/data/a/b") and m.is_allowed(BASE, "/srv/data"), "inside")
    expect(not any(m.is_allowed(BASE, path) for path in
                   ("/srv/data2", "/srv", "/srv/data/../etc", "/etc/passwd")), "outside")


if __name__ == "__main__":
    run_checks(load, [("safe-path-join", "containment-safe single join", join_check),
                      ("path-resolution", "multi-part resolution and typed escape", resolution_check),
                      ("containment-policy", "inside/outside containment policy", policy_check),
                      ("path-integration", "resolved path is allowed",
                       lambda m: expect(m.is_allowed(BASE, m.resolve_within(BASE, ["reports", "2026", "q1.csv"])),
                                        "integration"))])
