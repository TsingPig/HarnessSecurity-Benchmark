"""Run one mechanism across the six pinned paper harnesses."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
from aa import aa_reviewer
import harness_registry as registry
from native_profiles import native_toggle_policy
from run_agent import benchmark_main, load_repo_env, pick_env, write_report, ENV_OVERRIDES

@contextlib.contextmanager
def harness_environment(harness_id, profile):
    """Profiles contain names of environment variables, never credential values."""
    prefix = harness_id.upper().replace("-", "_") + "_"
    dot = load_repo_env()
    overrides = {}
    allowed = {"model_env", "base_url_env", "api_key_env", "env", "agent_home_dir", "extra_cli"}
    if set(profile) - allowed:
        raise ValueError(f"Unknown profile fields: {sorted(set(profile) - allowed)}")
    for suffix in ("MODEL", "BASE_URL", "API_KEY"):
        source = profile.get(suffix.lower() + "_env", prefix + suffix)
        if not isinstance(source, str) or not source.replace("_", "").isalnum():
            raise ValueError("Profile values must be environment variable names")
        value = pick_env(dot, source)
        if value:
            overrides["AGENT_" + suffix] = value
    env_map = profile.get("env", {})
    allowlist = registry.load(harness_id).get("env_allowlist", [])
    for target, source in env_map.items():
        if target not in allowlist or not isinstance(source, str) or not source.replace("_", "").isalnum():
            raise ValueError("Native profile mapping must use allowlisted target and source env names")
        overrides[target] = pick_env(dot, source) or ""
    token = ENV_OVERRIDES.set(overrides)
    try:
        yield
    finally:
        ENV_OVERRIDES.reset(token)

def _stable_run_arguments(arguments):
    """Exclude the batch size and concurrency that benchmark_main permits on resume."""
    stable = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in ("--attempts", "-k", "--jobs"):
            index += 2
            continue
        if argument.startswith(("--attempts=", "--jobs=", "-k=")):
            index += 1
            continue
        stable.append(argument)
        index += 1
    return stable

def matrix_main(mechanism, dataset, oracle, argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harnesses", nargs="+", default=["all"])
    parser.add_argument("--profiles", type=Path, help="JSON keyed by canonical harness ID; env names only")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args, common = parser.parse_known_args(argv)
    if "--harness" in common:
        parser.error("Use --harnesses for a study matrix")
    all_ids = [row["id"] for row in registry.population()]
    selected = all_ids if args.harnesses == ["all"] else [registry.canonical_id(x) for x in args.harnesses]
    if len(set(selected)) != len(selected) or set(selected) - set(all_ids):
        parser.error("Unknown or duplicate harness selection (codex aliases codex-cli)")
    population = {r["harness_id"]: r for r in registry.validate(selected)}
    profiles = json.loads(args.profiles.read_text(encoding="utf-8")) if args.profiles else {}
    if set(profiles) - set(all_ids):
        parser.error("Profiles must use canonical harness IDs")
    signature = {"mechanism": mechanism, "harnesses": selected, "arguments": common, "profiles": profiles}
    stable_signature = {**signature, "arguments": _stable_run_arguments(common)}
    fingerprint = hashlib.sha256(json.dumps(stable_signature, sort_keys=True).encode()).hexdigest()
    out = args.out.resolve()
    report_path = out / "study.json"
    previous = None
    if not args.dry_run:
        if args.resume:
            previous = json.loads(report_path.read_text(encoding="utf-8"))
            previous_signature = previous.get("config", {})
            comparable = {**previous_signature,
                          "arguments": _stable_run_arguments(previous_signature.get("arguments", []))}
            if comparable != stable_signature:
                parser.error("Study selection/profile differs; use a new output directory")
        elif out.exists() and any(out.iterdir()):
            parser.error("Study output must be empty, or use --resume")
    report = {"schema_version": 1, "fingerprint": fingerprint, "config": signature,
              "status": "planned" if args.dry_run else "running", "harnesses": [],
              "note": "Blocked/unmeasured harnesses remain in the population; rates are per harness."}
    if previous is not None:
        report["resume_history"] = [*(previous.get("resume_history") or []),
                                    {"from": previous["config"]["arguments"], "to": common}]
    # Validate the mechanism/task matrix once even when every requested adapter is blocked.
    with contextlib.redirect_stdout(io.StringIO()):
        base_plan = benchmark_main(mechanism, dataset, oracle, [*common, "--dry-run"])
    if not args.dry_run:
        write_report(report_path, report)
    # D/A are single-arm, C/O paired, and U remains unmeasured.
    units_per_mode = len(base_plan["config"]["tasks"]) * base_plan["config"]["attempts"]
    report["runs_per_harness"] = {}
    report["planned_runs"] = 0
    for harness_id in selected:
        row = {**population[harness_id], "status": "planned", "report": f"{harness_id}/report.json"}
        if not row["recipe_available"]:
            report["runs_per_harness"][harness_id] = 0
            row["status"] = "blocked_adapter"
            report["harnesses"].append(row)
            continue
        meta = registry.load(harness_id)
        requested = None
        if "--modes" in common:
            requested = []
            for value in common[common.index("--modes") + 1:]:
                if value.startswith("-"):
                    break
                requested.append(value)
        policy = native_toggle_policy(meta, mechanism, requested)
        row["mode_policy"] = policy
        count = units_per_mode * len(policy["modes"]) if policy["status"] == "ready" else 0
        report["runs_per_harness"][harness_id] = count
        report["planned_runs"] += count
        report["harnesses"].append(row)
        if policy and policy["status"] != "ready":
            row.update(status=policy["status"], blockers=[policy["reason"]])
        else:
            options = [*common, "--harness", harness_id, "--out", str(out / harness_id)]
            profile = profiles.get(harness_id, {})
            if profile.get("agent_home_dir"):
                options += ["--agent-home-dir", profile["agent_home_dir"]]
            options += ["--agent-extra-cli=" + arg for arg in profile.get("extra_cli", [])]
            if args.dry_run:
                options += ["--dry-run"]
            elif args.resume and (out / harness_id / "report.json").exists():
                options += ["--resume"]
            try:
                with harness_environment(harness_id, profile):
                    if args.dry_run:
                        with contextlib.redirect_stdout(io.StringIO()):
                            result = benchmark_main(mechanism, dataset, oracle, options)
                        row["fingerprint"] = result["fingerprint"]
                        row["status"] = result["status"]
                        row["planned_runs"] = len(result["planned_runs"])
                    else:
                        result = benchmark_main(mechanism, dataset, oracle, options)
                        row.update(status=result["status"], summary=result.get("summary"),
                                   metrics=result.get("metrics"), measurement_status=result.get("measurement_status"))
                        row["runtime_verified"] = bool(result.get("summary", {}).get("completed"))
            except (ValueError, OSError, SystemExit) as error:
                row.update(status="blocked_preflight", blockers=[str(error)])
        if not args.dry_run:
            write_report(report_path, report)
    report["coverage"] = {"registered": len(selected),
                          "recipes": sum(r["recipe_available"] for r in report["harnesses"]),
                          "runtime_verified": sum(r["runtime_verified"] for r in report["harnesses"]),
                          "blocked": sum(r["status"].startswith("blocked") for r in report["harnesses"])}
    if not args.dry_run:
        report["status"] = "completed" if all(r["status"] == "completed" for r in report["harnesses"]) else "incomplete"
        write_report(report_path, report)
    if args.dry_run:
        display_rows = []
        for row in report["harnesses"]:
            display = {"harness_id": row["harness_id"], "status": row["status"]}
            if row["status"].startswith("blocked"):
                display["reason"] = (row.get("blockers") or ["blocked"])[0]
            else:
                display["planned_runs"] = row.get("planned_runs", report["runs_per_harness"].get(
                    row["harness_id"], 0))
            display_rows.append(display)
        printed = {"status": report["status"], "planned_runs": report["planned_runs"],
                   "harnesses": display_rows, "coverage": report["coverage"]}
    else:
        printed = {"study": str(report_path), "coverage": report["coverage"],
                   "status": report["status"]}
    print(json.dumps(printed, ensure_ascii=False, indent=2))
    return report
