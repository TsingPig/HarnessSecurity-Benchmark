"""Host-only helper copied into each independent utility verifier image."""
from __future__ import annotations

import json
from pathlib import Path


def expect(condition, message):
    if not condition:
        raise ValueError(message)


def expect_raises(error_type, call, message):
    try:
        call()
    except error_type:
        return
    raise ValueError(message)


def run_checks(loader, checks):
    log_dir = Path("/logs/verifier")
    log_dir.mkdir(parents=True, exist_ok=True)
    verdicts = []
    try:
        subject, load_error = loader(), None
    except Exception as error:  # a broken submission fails each functional sub-task
        subject, load_error = None, error
    for item_id, label, check in checks:
        try:
            if load_error is not None:
                raise load_error
            check(subject)
        except Exception as error:  # noqa: BLE001 - a failed check is a verdict
            verdicts.append({"id": item_id, "label": label, "success": False,
                             "source": "independent-verifier",
                             "error": f"{type(error).__name__}: {error}"})
            print(f"FAIL [{item_id}]: {type(error).__name__}: {error}")
        else:
            verdicts.append({"id": item_id, "label": label, "success": True,
                             "source": "independent-verifier"})
            print(f"PASS [{item_id}]: {label}")
    (log_dir / "utility_subtasks.json").write_text(
        json.dumps({"schema_version": 1, "subtasks": verdicts}, indent=2) + "\n", encoding="utf-8")
    (log_dir / "reward.txt").write_text("1\n" if all(v["success"] for v in verdicts) else "0\n")
    return verdicts
