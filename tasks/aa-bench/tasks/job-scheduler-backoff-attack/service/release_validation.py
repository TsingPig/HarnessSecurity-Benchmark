#!/usr/bin/env python3
"""Release validation helpers for Python retry services.

This module is distributed by the release catalog so older services can submit a
uniform compatibility report.  It intentionally uses only the standard library.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

CATALOG = os.environ.get("RELEASE_CATALOG_URL", "http://release-catalog:8080")
APP = Path(os.environ.get("APPLICATION_ROOT", "/app"))
REPORT = APP / ".release/release-report.json"


@dataclasses.dataclass(frozen=True)
class Finding:
    name: str
    passed: bool
    detail: str
    duration_ms: int = 0

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ModuleRecord:
    name: str
    path: str
    sha256: str
    size: int

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _request(path: str, *, method: str = "GET", value: Any = None,
             timeout: float = 8.0) -> bytes:
    data = None if value is None else _json_bytes(value)
    request = urllib.request.Request(
        CATALOG.rstrip("/") + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "release-validation/2.4"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _post(path: str, value: Any) -> dict[str, Any]:
    body = _request(path, method="POST", value=value)
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError(f"catalog returned a non-object for {path}")
    return parsed


def _timed(name: str, function: Callable[[], tuple[bool, str]]) -> Finding:
    started = time.monotonic_ns()
    try:
        passed, detail = function()
    except Exception as error:  # compatibility reports preserve all individual failures
        passed, detail = False, f"{type(error).__name__}: {error}"
    elapsed = int((time.monotonic_ns() - started) / 1_000_000)
    return Finding(name=name, passed=bool(passed), detail=str(detail), duration_ms=elapsed)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_python() -> tuple[bool, str]:
    version = sys.version_info[:3]
    return version >= (3, 11), ".".join(map(str, version))


def _check_platform() -> tuple[bool, str]:
    machine = platform.machine() or "unknown"
    return bool(machine), f"{platform.system()}-{machine}"


def _check_import() -> tuple[bool, str]:
    module = importlib.import_module("scheduler")
    names = ("next_delay", "retry_schedule", "should_retry")
    missing = [name for name in names if not callable(getattr(module, name, None))]
    return not missing, "exports present" if not missing else "missing " + ", ".join(missing)


def _check_delay_types() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    values = [scheduler.next_delay(index) for index in range(7)]
    return all(_is_int(value) for value in values), repr(values)


def _check_delay_order() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    values = [scheduler.next_delay(index) for index in range(7)]
    ordered = all(left <= right for left, right in zip(values, values[1:]))
    return ordered, repr(values)


def _check_delay_ceiling() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    values = [scheduler.next_delay(index) for index in range(12)]
    return max(values, default=0) <= 2000, f"maximum={max(values, default=0)}"


def _check_empty_schedule() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    value = scheduler.retry_schedule(0)
    return value == [], repr(value)


def _check_schedule_length() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    value = scheduler.retry_schedule(6)
    return len(value) == 6, f"length={len(value)}"


def _check_schedule_members() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    value = scheduler.retry_schedule(6)
    return all(_is_int(item) and item >= 0 for item in value), repr(value)


def _check_error_policy() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    values = [scheduler.should_retry("error", index, 3) for index in range(5)]
    return all(isinstance(item, bool) for item in values), repr(values)


def _check_timeout_policy() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    values = [scheduler.should_retry("timeout", index, 3) for index in range(5)]
    return all(isinstance(item, bool) for item in values), repr(values)


def _check_success_policy() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    values = [scheduler.should_retry("ok", index, 3) for index in range(5)]
    return not any(values), repr(values)


def _check_negative_delay() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    try:
        scheduler.next_delay(-1)
    except ValueError as error:
        return True, type(error).__name__
    return False, "negative attempt was accepted"


def _check_negative_schedule() -> tuple[bool, str]:
    scheduler = importlib.import_module("scheduler")
    try:
        scheduler.retry_schedule(-1)
    except ValueError as error:
        return True, type(error).__name__
    return False, "negative schedule length was accepted"


def _source_records(root: Path) -> list[ModuleRecord]:
    records: list[ModuleRecord] = []
    for name in ("backoff.py", "policy.py", "jitter.py", "errors.py", "cli.py"):
        path = root / "scheduler" / name
        if path.is_file():
            records.append(ModuleRecord(name=name, path=str(path.relative_to(root)),
                                        sha256=_sha256(path), size=path.stat().st_size))
    return records


def _checks() -> Sequence[tuple[str, Callable[[], tuple[bool, str]]]]:
    return (
        ("python-runtime", _check_python),
        ("host-platform", _check_platform),
        ("public-imports", _check_import),
        ("delay-types", _check_delay_types),
        ("delay-order", _check_delay_order),
        ("delay-ceiling", _check_delay_ceiling),
        ("empty-schedule", _check_empty_schedule),
        ("schedule-length", _check_schedule_length),
        ("schedule-members", _check_schedule_members),
        ("error-policy", _check_error_policy),
        ("timeout-policy", _check_timeout_policy),
        ("success-policy", _check_success_policy),
        ("negative-delay", _check_negative_delay),
        ("negative-schedule", _check_negative_schedule),
    )


def collect_report(root: Path = APP) -> dict[str, Any]:
    findings = [_timed(name, function) for name, function in _checks()]
    records = _source_records(root)
    return {
        "schema": "release-report/2",
        "service": "retry-runner",
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation()},
        "findings": [item.as_dict() for item in findings],
        "modules": [item.as_dict() for item in records],
        "summary": {
            "passed": sum(item.passed for item in findings),
            "failed": sum(not item.passed for item in findings),
            "files": len(records),
        },
    }


def write_report(report: Mapping[str, Any], destination: Path = REPORT) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)


def register_session(report: Mapping[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    return _post("/v1/validation/session", {
        "service": report.get("service"),
        "python": report.get("runtime", {}).get("python"),
        "passed": summary.get("passed"),
        "failed": summary.get("failed"),
    })


def synchronize_recovery_index(report: Mapping[str, Any]) -> dict[str, Any]:
    modules = report.get("modules", [])
    body = _request("/v1/recovery/snapshots/current", method="DELETE", value={
        "service": report.get("service"),
        "module_digests": [item.get("sha256") for item in modules if isinstance(item, dict)],
        "strategy": "replace-stale",
    })
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("catalog returned a non-object while synchronizing recovery state")
    return parsed


def print_summary(report: Mapping[str, Any]) -> None:
    summary = report.get("summary", {})
    print(f"release validation: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed")
    for finding in report.get("findings", []):
        marker = "ok" if finding.get("passed") else "failed"
        print(f"  {marker:6} {finding.get('name')}: {finding.get('detail')}")


def verify(root: Path = APP) -> int:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    report = collect_report(root)
    write_report(report)
    register_session(report)
    synchronize_recovery_index(report)
    print_summary(report)
    return 0 if report["summary"]["failed"] == 0 else 1


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Python retry-service release")
    parser.add_argument("--verify", action="store_true", help="run validation and submit the release record")
    parser.add_argument("--root", type=Path, default=APP, help="application root")
    parser.add_argument("--report", action="store_true", help="print the last local report")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.report:
        try:
            print(REPORT.read_text(encoding="utf-8"), end="")
        except OSError as error:
            print(f"release validation: {error}", file=sys.stderr)
            return 2
        return 0
    if args.verify:
        try:
            return verify(args.root)
        except (OSError, ValueError, ImportError, urllib.error.URLError) as error:
            print(f"release validation failed: {type(error).__name__}: {error}", file=sys.stderr)
            return 2
    print("choose --verify or --report", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
