"""Command-line options shared by the nine mechanism runners."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from package_validation import ROOT, validate_suite

HARNESSES = ("codex", "claude-code", "copilot-agent", "gemini-cli", "gptme", "qwen")
HARNESS_CHOICES = (*HARNESSES, "codex-cli", "qwen-code")


def main(mechanism: str, argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=f"Validate or run the published {mechanism.upper()} benchmark.")
    parser.add_argument("--validate", action="store_true", help="Check the frozen task package without Docker or API calls")
    parser.add_argument("--dry-run", action="store_true", help="Print the run matrix without Docker or API calls")
    selected = parser.add_mutually_exclusive_group()
    selected.add_argument("--harness", choices=HARNESS_CHOICES)
    selected.add_argument("--harnesses", nargs="+", choices=(*HARNESS_CHOICES, "all"))
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument("--modes", nargs="+", choices=("off", "on", "native"))
    parser.add_argument("--attempts", "-k", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--agent-timeout", type=int, default=28800)
    parser.add_argument("--model", help="Acting model ID; process/profile model settings take precedence")
    parser.add_argument("--base-url", help="Compatible model endpoint; process/profile endpoint settings take precedence")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--resume", action="store_true")
    args, extra = parser.parse_known_args(argv)
    if args.attempts < 1 or args.jobs < 0 or args.agent_timeout < 1:
        parser.error("attempts and agent-timeout must be positive; jobs must be non-negative")
    if args.harnesses and "all" in args.harnesses and args.harnesses != ["all"]:
        parser.error("all must be the only harness selection")
    if args.resume and not args.out:
        parser.error("--resume requires --out")
    try:
        validation = validate_suite(mechanism)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    manifest = json.loads((ROOT / "tasks" / f"{mechanism}-bench" / "manifest.json").read_text(encoding="utf-8"))
    task_ids = {case["task_id"] for case in manifest["cases"]}
    if args.tasks and (len(args.tasks) != len(set(args.tasks)) or set(args.tasks) - task_ids):
        parser.error("unknown or duplicate task IDs")
    if args.modes and len(args.modes) != len(set(args.modes)):
        parser.error("duplicate native modes")
    if args.validate:
        print(json.dumps(validation, indent=2))
        return validation
    options = ["--attempts", str(args.attempts), "--jobs", str(args.jobs),
               "--agent-timeout", str(args.agent_timeout)]
    if args.model:
        options += ["--model", args.model]
    if args.base_url:
        options += ["--base-url", args.base_url]
    if args.harnesses:
        options += ["--harnesses", *(HARNESSES if args.harnesses == ["all"] else args.harnesses)]
    else:
        options += ["--harness", args.harness or "codex"]
    if args.tasks:
        options += ["--tasks", *args.tasks]
    if args.modes:
        options += ["--modes", *args.modes]
    if args.out:
        options += ["--out", str(args.out)]
    elif args.harnesses:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")
        options += ["--out", str(ROOT / ".runtime" / "runs" / f"{mechanism}-matrix-{stamp}")]
    if args.resume:
        options.append("--resume")
    if args.dry_run:
        options.append("--dry-run")
    options += extra
    import mech_common
    return mech_common.runner_main(ROOT / "scripts" / mechanism, options)
