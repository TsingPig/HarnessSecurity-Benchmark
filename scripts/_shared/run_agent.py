#!/usr/bin/env python3
"""Run a mechanism and harness evaluation without Harbor.

Each attempt runs one task and one harness in a disposable Docker container.
Native tasks build environment/Dockerfile before the harness is installed on
top; legacy tasks use environment/app. The agent works in the image's WORKDIR
and retains its native approval and sandbox policies unless extra CLI options
are explicitly supplied. Verifiers evaluate the workspace after the agent exits.

Mechanism metadata is declared in scripts/<mech>/mech.json; harness images
and launch commands are declared in scripts/_shared/harness/<id>/harness.json.
Public batch execution uses scripts/<mech>/<mech>_run_agent.py, including independent
verification, stopped-container snapshots, checkpoints, and resume support.
The single-attempt CLI also retains same-container verification compatibility.

Each attempt creates a container, copies its instructions, runs the agent,
uploads and runs verifiers, retrieves artifacts, and removes the container
unless --keep is set. Verifier materials are uploaded only after the agent
exits. Credentials use an explicit allowlist and are redacted from console logs.
AGENT_* settings and native provider credentials are forwarded directly.

Default output: <repo>/.runtime/runs/<mech>/<harness>/<task>/<timestamp>_a<attempt>/
    manifest.json    Parameters, versions, provenance, and verdicts.
    console.log      Host-side Docker command output.
    container_run.sh The executed container script.
    app/ or artifacts/ Workspace and requested artifact paths.
    logs/            verifier/{reward.txt,boundary.json} and agent/*.log.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import ipaddress
import json
import os
import shlex
import subprocess
import sys
import tarfile
import threading
import tomllib
import uuid
import time
import re
from concurrent import futures
from contextvars import ContextVar, copy_context
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from metrics import print_trial_details, report_metrics
from subtask_metrics import attach_trial_scores, utility_subtasks_from_ctrf, validate_subtasks
from process_utils import run_bounded
from docker_builder import stage_context
from package_validation import validate_suite
import harness_registry
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aa import aa_reviewer
from trace_formats import provider_diagnostics, token_telemetry

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HARNESS_DIR = HERE / "harness"
MECH_DIR = REPO / "scripts"
DEFAULT_OUT = REPO / ".runtime" / "runs"
# Only allowlisted host settings are forwarded; logs redact their values.
AGENT_SETTINGS = ("AGENT_API_KEY", "AGENT_BASE_URL", "AGENT_MODEL")
ENV_OVERRIDES = ContextVar("harness_profile", default={})


def gemini_native_sandbox_paths(task: Path) -> tuple[str, ...]:
    """Return task-image paths explicitly exposed to Gemini's nested sandbox."""
    spec_path = task / "task.toml"
    if not spec_path.is_file():
        return ()
    spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    raw_paths = (spec.get("agent") or {}).get("native_sandbox_mounts", [])
    if not isinstance(raw_paths, list):
        raise ValueError("agent.native_sandbox_mounts must be a list of absolute paths")
    paths: list[str] = []
    for raw_path in raw_paths:
        if not isinstance(raw_path, str):
            raise ValueError("agent.native_sandbox_mounts must contain only strings")
        path = PurePosixPath(raw_path)
        if not path.is_absolute() or path == PurePosixPath("/") or ".." in path.parts:
            raise ValueError(f"Invalid Gemini native sandbox mount path: {raw_path!r}")
        normalized = str(path)
        if normalized not in paths:
            paths.append(normalized)
    return tuple(paths)


def gemini_native_sandbox_mount_flags(volume_mountpoint: str,
                                     paths: tuple[str, ...]) -> list[str]:
    """Bind staged task-image paths into Gemini's nested sandbox read-only."""
    root = PurePosixPath(volume_mountpoint)
    flags: list[str] = []
    for raw_path in paths:
        path = PurePosixPath(raw_path)
        if (not root.is_absolute() or not path.is_absolute() or path == PurePosixPath("/")
                or ".." in root.parts or ".." in path.parts):
            raise ValueError("Gemini native sandbox mounts require safe absolute paths")
        source = str(root.joinpath(*path.parts[1:]))
        flags.extend(("--volume", f"{source}:{path}:ro"))
    return flags



def configure_gemini_model_proxy(env: dict[str, str]) -> dict[str, str]:
    """Restrict the Gemini NI CONNECT proxy to its configured HTTPS model endpoint."""
    command = env.get("GEMINI_SANDBOX_PROXY_COMMAND")
    if not command:
        return env
    endpoint = urlsplit(env.get("GOOGLE_GEMINI_BASE_URL")
                        or "https://generativelanguage.googleapis.com")
    if endpoint.scheme != "https" or not endpoint.hostname:
        raise ValueError("Gemini NI requires an HTTPS model endpoint for CONNECT isolation")
    model_host = endpoint.hostname
    if ":" in model_host:
        model_host = str(ipaddress.IPv6Address(model_host))
    else:
        model_host = model_host.encode("idna").decode("ascii").lower()
        if not re.fullmatch(r"[a-z0-9.-]+", model_host):
            raise ValueError("Gemini NI model endpoint has an invalid hostname")
    model_port = endpoint.port if endpoint.port is not None else 443
    if not 1 <= model_port <= 65535:
        raise ValueError("Gemini NI model endpoint has an invalid port")
    proxy_args = shlex.split(command)
    if len(proxy_args) != 3 or proxy_args[:2] != ["node", "-e"]:
        raise ValueError("Gemini sandbox proxy recipe must be a Node inline command")
    script = proxy_args[2]
    if script.count("__MODEL_HOST_JSON__") != 2 or script.count("__MODEL_PORT__") != 2:
        raise ValueError("Gemini sandbox proxy recipe lacks model endpoint placeholders")
    proxy_args[2] = script.replace("__MODEL_HOST_JSON__", json.dumps(model_host))
    proxy_args[2] = proxy_args[2].replace("__MODEL_PORT__", str(model_port))
    return {**env, "GEMINI_SANDBOX_PROXY_COMMAND": shlex.join(proxy_args)}


def load_repo_env() -> dict[str, str]:
    """Runtime settings are supplied through the process environment."""
    return {}


def pick_env(dot: dict[str, str], name: str) -> str | None:
    """Prefer explicit profile overrides, then supplied settings and process variables."""
    overrides = ENV_OVERRIDES.get()
    return overrides[name] if name in overrides else (dot.get(name) if name in dot else os.environ.get(name))


def runtime_settings(args: argparse.Namespace, dot: dict[str, str]) -> dict[str, str]:
    """Include CLI model/endpoint fallbacks before deriving native provider settings."""
    settings = dict(dot)
    for name, value in (("AGENT_MODEL", args.model), ("AGENT_BASE_URL", args.base_url)):
        if value and not pick_env(dot, name):
            settings[name] = value
    return settings


def credential_values(dot: dict[str, str], harness: dict) -> tuple[str, ...]:
    names = {"AGENT_API_KEY", "REVIEWER_API_KEY", *harness.get("env_allowlist", [])}
    return tuple(dict.fromkeys(
        value for name in names
        if any(part in name.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH"))
        if (value := pick_env(dot, name))))


def redact_log_file(path: Path, secrets: tuple[str, ...]) -> None:
    """Mask configured credentials in captured logs without touching task snapshots."""
    if not path.is_file() or not secrets:
        return
    data = path.read_bytes()
    clean = data
    for secret in sorted(secrets, key=len, reverse=True):
        representations = {secret, json.dumps(secret, ensure_ascii=False)[1:-1],
                           json.dumps(secret, ensure_ascii=True)[1:-1]}
        for value in representations:
            clean = clean.replace(value.encode("utf-8"), b"<redacted>")
    if clean != data:
        path.write_bytes(clean)


def resume_config_relation(previous: dict, current: dict) -> str | None:
    """Classify a resume configuration as exact or a monotonic matrix extension."""
    if previous == current:
        return "exact"
    previous_attempts = previous.get("attempts")
    current_attempts = current.get("attempts")
    if (not isinstance(previous_attempts, int) or isinstance(previous_attempts, bool)
            or not isinstance(current_attempts, int) or isinstance(current_attempts, bool)
            or current_attempts < previous_attempts):
        return None
    previous_modes = previous.get("modes")
    current_modes = current.get("modes")
    if (not isinstance(previous_modes, list) or not isinstance(current_modes, list)
            or not set(previous_modes).issubset(current_modes)):
        return None
    normalized_previous = dict(previous)
    normalized_previous["attempts"] = current_attempts
    normalized_previous["modes"] = current_modes
    previous_policy = previous.get("mode_policy")
    current_policy = current.get("mode_policy")
    if isinstance(previous_policy, dict) and isinstance(current_policy, dict):
        previous_policy_modes = previous_policy.get("modes")
        current_policy_modes = current_policy.get("modes")
        if (not isinstance(previous_policy_modes, list) or not isinstance(current_policy_modes, list)
                or not set(previous_policy_modes).issubset(current_policy_modes)):
            return None
        normalized_previous["mode_policy"] = {**previous_policy, "modes": current_policy_modes}
    if normalized_previous == current:
        return "extension"
    return None


def bridge_env(meta: dict, dot: dict[str, str]) -> dict[str, str]:
    """Map existing credentials to the native CLI variables declared in auth_bridge.

    Sources must name variables in the process environment. Targets
    must already appear in the harness env_allowlist. Explicit target settings
    take precedence. The bridge neither creates keys nor modifies the host
    environment. Missing sources are handled by the CLI auth_any preflight.
    """
    result: dict[str, str] = {}
    if any(not pick_env(dot, name) for name in meta.get("auth_bridge_requires", [])):
        return result
    allowlist = set(meta.get("env_allowlist", ()))
    for target, source in (meta.get("auth_bridge") or {}).items():
        label = f"{meta.get('id', '?')}: auth_bridge"
        if target not in allowlist:
            raise ValueError(f"{label} target {target} is not in env_allowlist")
        if not isinstance(source, str) or not source.replace("_", "").isalnum():
            raise ValueError(f"{label} source must be an environment variable name: {source!r}")
        value = pick_env(dot, target) or pick_env(dot, source)
        if value:
            result[target] = value
    return result


def log(msg: str) -> None:
    """Write a progress line to stderr and flush immediately."""
    print(msg, file=sys.stderr, flush=True)


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Capture an external command's stdout and stderr as text."""
    kw.setdefault("timeout", 120)
    return run_bounded(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def docker(*args: str, **kw) -> subprocess.CompletedProcess:
    """Run a Docker command through the subprocess wrapper."""
    return sh(["docker", *args], **kw)


def check_docker() -> str:
    """Return the Docker server version, or exit if Docker is unavailable."""
    probe = docker("version", "--format", "{{.Server.Version}}")
    if probe.returncode != 0:
        raise SystemExit(
            "Docker is unavailable or its daemon is not running.\n" + (probe.stderr or probe.stdout or "").strip()
        )
    return probe.stdout.strip()


def cleanup_native_sandbox(manifest: dict, run) -> list[str]:
    """Remove only the nested Docker resources recorded for this NI trial."""
    if not manifest.get("workspace_volume"):
        return []
    errors = []

    def remove(arguments: list[str], label: str):
        try:
            result = run(arguments, label)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            errors.append(f"{label}: {error}")
            return None
        missing = any(marker in (result.stderr or "").lower()
                      for marker in ("no such container", "no such network", "no such volume"))
        if result.returncode and not missing:
            errors.append(f"{label}: exit {result.returncode}")
        return result

    container = manifest.get("container")
    if container:
        remove(["rm", "-f", container + "-sandbox"], "cleanup-native-sandbox")
    network = manifest.get("gemini_sandbox_network")
    if network:
        members = remove(["ps", "-aq", "--filter", f"network={network}"], "cleanup-native-members")
        if members is not None and not members.returncode:
            for member in members.stdout.split():
                remove(["rm", "-f", member], f"cleanup-native-member-{member}")
        remove(["rm", "-f", network + "-proxy"], "cleanup-native-proxy")
        for name in (network, network + "-proxy"):
            remove(["network", "rm", name], f"cleanup-native-network-{name}")
    for key in ("workspace_volume", "sandbox_support_volume"):
        if manifest.get(key):
            remove(["volume", "rm", manifest[key]], f"cleanup-native-{key}")
    return errors


# --------------------------------------------------------------------------- #
# Recipes declare harness images and launch commands, and mechanism task locations.
# Add a recipe directory to register a new harness or mechanism.
# The common runner does not need a new case for each recipe.
# --------------------------------------------------------------------------- #
def load_harness(harness_id: str) -> dict:
    """Read the image and launch recipe from harness/<id>/harness.json."""
    return harness_registry.load(harness_id, HARNESS_DIR)


def load_mechanism(mech: str) -> dict:
    """Read task locations and naming rules from mechanisms/<mech>/mech.json."""
    meta = MECH_DIR / mech / "mech.json"
    if not meta.exists():
        raise SystemExit(f"Unknown mechanism {mech!r}: {meta} does not exist")
    return json.loads(meta.read_text(encoding="utf-8"))


def mechanism_mode_env(args: argparse.Namespace, harness: dict, *,
                       allow_unverified_approval: bool = False) -> dict[str, str]:
    """Resolve the selected strict or permissive mode into container variables.

    Use mech.json for the mechanism key and injection variable, and harness.json
    for its on/off profile. Recorded implementation classifications constrain execution: D runs on,
    A runs off, and C/O requires distinct configurations. A profile can be a CLI
    string or an object containing args and env settings.
    """
    mode = getattr(args, "mode", None)
    if not mode or not args.mechanism:
        return {}
    mech = load_mechanism(args.mechanism)
    key = mech.get("mechanism_key", mech.get("id"))
    env_var = mech.get("mech_args_env", "HARNESS_MECH_ARGS")
    spec = (harness.get("mechanisms") or {}).get(key) or {}
    from native_profiles import native_toggle_policy
    profile = native_toggle_policy(harness, args.mechanism, [mode],
                                   allow_unverified_approval=allow_unverified_approval,
                                   assume_gemini_pt_configurable=getattr(args, "assume_gemini_pt_configurable", False))
    if profile["status"] != "ready":
        raise ValueError(f"{harness['id']}: {profile['reason']}")
    if mode not in spec and profile["rating"] in ("D", "A"):
        return {}
    if mode not in spec:
        raise SystemExit(f"Harness {harness.get('id')!r} mechanism {key!r} lacks mode {mode!r}")
    value = spec[mode]
    if isinstance(value, dict):
        out = dict(value.get("env") or {})
        if "args" in value:
            out[env_var] = value["args"]
        return out
    return {env_var: value}


def resolve_task_dir(args: argparse.Namespace) -> Path:
    """Resolve --task first, otherwise combine mechanism, task ID, and condition.

    Explicit task paths take precedence. Otherwise use the mechanism's tasks_dir
    and task_pattern, for example wb + session-window-debug + attack.
    """
    if args.task is not None:
        task = Path(args.task)
        return task if task.is_absolute() else (REPO / task)
    if args.mechanism is None or args.condition is None:
        raise SystemExit("Provide --task <directory>, or both --mechanism and --condition")
    mech = load_mechanism(args.mechanism)
    tasks_dir = Path(mech["tasks_dir"])
    if not tasks_dir.is_absolute():
        tasks_dir = REPO / tasks_dir
    pattern = mech.get("task_pattern", "{condition}")
    if "{task_id}" in pattern and not args.task_id:
        raise SystemExit("This mechanism has multiple tasks; provide --task-id or --task")
    return tasks_dir / pattern.format(condition=args.condition, task_id=args.task_id)


def resolve_agent_home(args: argparse.Namespace, harness: dict) -> Path | None:
    """Choose the host directory used to seed the container's agent home.

    Prefer explicit --agent-home-dir, then the harness recipe's agent_home
    directory containing non-secret provider settings; otherwise return None.
    """
    if args.agent_home_dir is not None:
        p = Path(args.agent_home_dir)
        if not p.is_absolute():
            p = (REPO / p).resolve()
        if not p.exists():
            raise SystemExit(f"--agent-home-dir does not exist: {args.agent_home_dir}")
        return p
    rel = harness.get("agent_home")
    if rel:
        bundled = (HARNESS_DIR / harness_registry.recipe_id(args.harness) / rel).resolve()
        if bundled.exists():
            return bundled
        log(f"[warn] Harness {args.harness!r} declares missing agent_home={rel!r}; skipping home setup")
    return None

# ============================================================================= #
# Build Bash scripts executed inside the container.
# Use the harness recipe and run directory to assemble the required commands.
# ============================================================================= #

def build_verdict_script() -> str:
    """Build the container verifier script.

    The host uploads tests/ and this script only after the agent exits, so the
    agent cannot inspect verifier code or expected outputs during execution.
    """
    return """#!/bin/bash
# Prefer the task verifier entrypoint; otherwise use the pilot dual-oracle convention.
# Utility: pytest -> reward.txt; security boundary: boundary.json.
if [ -f /tests/run_verifiers.sh ]; then
  echo "[verdict] running task run_verifiers.sh"
  bash /tests/run_verifiers.sh
elif [ -f /tests/test.sh ]; then
  echo "[verdict] running task test.sh"
  bash /tests/test.sh
else
  echo "[verdict] running utility verifier (fallback)"
  python3 -m pytest -q /tests/test_utility.py >/logs/agent/verdict_utility.log 2>&1
  UTIL=$?
  echo "[verdict] running boundary verifier (fallback)"
  python3 /tests/check_boundary.py
  if [ "$UTIL" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
fi
echo "reward=$(cat /logs/verifier/reward.txt 2>/dev/null || echo missing)"
exit 0
"""


def aa_on_requires_pty(args, harness: dict) -> bool:
    """Return whether this harness's native AA-ON mode needs a terminal."""
    aa_spec = (harness.get("mechanisms") or {}).get("auto_approve_mode") or {}
    return (getattr(args, "mechanism", None) == "aa"
            and getattr(args, "mode", None) == "on"
            and aa_spec.get("on_requires_pty") is True)


def build_container_script(harness: dict, run_dir: Path, workdir: str | None = None,
                           skip_verifiers: bool = False, agent_timeout: int = 0,
                           interactive: bool = False, structured: bool = False,
                           enforce_timeout: bool = False,
                           external_write_audit: bool = False) -> str:
    """Build the disposable container's agent execution script.

    Run optional task setup.sh, configure the agent home, and execute the recipe's
    unmodified run_command. It reads /scripts/instruction.md and runs in the task
    workspace; AGENT_MODEL and AGENT_EXTRA supply runtime options. Verification
    is separate: the host uploads tests/ and the verdict script after agent exit.
    """
    run_command = harness["run_command"]
    if agent_timeout and not structured and (not interactive or enforce_timeout):
        run_command = f"timeout --kill-after=10s {agent_timeout}s bash -c {shlex.quote(run_command)}"
    audit_setup = audit_begin = audit_end = ""
    if external_write_audit:
        from ro.write_audit import TRACE_BEGIN, TRACE_END, trace_command
        run_command = trace_command(run_command)
        audit_setup = "exec 4>&2\n"
        audit_begin = f"echo {shlex.quote(TRACE_BEGIN)} >&4\n"
        audit_end = f"echo {shlex.quote(TRACE_END)} >&4\n"
    change_dir = f"cd -- {shlex.quote(workdir)} || exit 1" if workdir else "# Inherit the image WORKDIR."
    # Export agent-home settings such as CODEX_HOME=/root/.codex and
    # optionally copy the supplied --agent-home-dir configuration into that home.
    home_env = harness.get("home_env", {})
    home_lines = "".join(f'export {k}={v}\nmkdir -p "${k}"\n' for k, v in home_env.items())
    preload = ""
    if home_env:
        first = next(iter(home_env))
        preload = (
            "if [ -d /root/.agent-preload ]; then "
            f'cp -a /root/.agent-preload/. "${first}"/ 2>/dev/null || true; fi\n'
        )
    verifier_handoff = ""
    if skip_verifiers:
        verifier_handoff = (
            "echo 'reward=deferred_to_offline_verifier'\n"
            "exit 0 # Utility verification runs in a separate container."
        )
    input_setup = ("# Preserve and initialize the native terminal for the host-side approval proxy.\n"
                   "export TERM=\"${TERM:-xterm-256color}\"\n"
                   "stty rows 40 cols 160 2>/dev/null || true\n"
                   if interactive else
                   "# Preserve raw stdin for the host-side structured approval protocol.\n"
                   if structured else
                   "# Non-interactive runs never expose the launcher's stdin to the agent.\n"
                   "exec 9<&0 0</dev/null\n")
    execution = ((f"( {run_command} ) >&3 2>&1\nAGENT_EXIT=$?\n") if interactive else
                 (f"( {run_command} ) >&3 2>/logs/agent/agent.stderr.log\n"
                  "AGENT_EXIT=$?\n") if structured else
                 (f"( {run_command} ) 2>&1 | tee /logs/agent/agent.log >&3\n"
                  "AGENT_EXIT=${PIPESTATUS[0]}\n"))
    return f"""#!/bin/bash
set -uo pipefail
# Keep stdout exclusively for the live agent trace; runner/verifier output uses stderr.
{audit_setup}exec 3>&1 1>&2
{input_setup}export DEBIAN_FRONTEND=noninteractive
mkdir -p /logs/verifier /logs/agent /scripts
# Harness images already contain python3, pytest, and git for verification.
# Optional setup.sh installs task-specific dependencies.
if [ -f /scripts/setup.sh ]; then
  echo "[setup] running task setup.sh"
  if ! bash /scripts/setup.sh >/logs/agent/setup.log 2>&1; then
    echo "setup.sh failed"
    tail -n 20 /logs/agent/setup.log
    echo 78 >/logs/agent/exit_code.txt
    : >/logs/agent/agent.log
    exit 0
  fi
fi
{home_lines}{preload}echo "[agent] running harness"
{change_dir}
{audit_begin}
{execution}echo "$AGENT_EXIT" >/logs/agent/exit_code.txt
{audit_end}
echo "agent_exit=$AGENT_EXIT"
{verifier_handoff}
# The host uploads and executes /scripts/verdict.sh only after the agent exits.
echo "reward=$(cat /logs/verifier/reward.txt 2>/dev/null || echo missing)"
exit 0
"""


def selected_model(args, dot, harness):
    """Do not send a gateway model ID to a product's unrelated hosted catalog."""
    meta = harness or {}
    native_auth = meta.get("native_model_when_authenticated")
    if meta.get("model_source") == "native" or (native_auth and pick_env(dot, native_auth)):
        name = harness_registry.canonical_id(meta["id"]).upper().replace("-", "_") + "_MODEL"
        return pick_env(dot, name) or ENV_OVERRIDES.get().get("AGENT_MODEL") or args.model
    return pick_env(dot, "AGENT_MODEL") or args.model


def aa_reviewer_model(args: argparse.Namespace, dot: dict[str, str], harness: dict,
                      acting_model: str | None) -> str | None:
    """Resolve AA-OFF's non-secret reviewer model ID; never forward reviewer credentials."""
    if getattr(args, "mechanism", None) != "aa" or getattr(args, "mode", None) != "off":
        return None
    spec = (harness.get("mechanisms") or {}).get("auto_approve_mode") or {}
    # Codex receives only the reviewer model ID on FD 9 and uses the acting
    # model's configured endpoint and credentials for its native review agent.
    if spec.get("off_reviewer") == "native_independent_ai":
        reviewer = pick_env(dot, "REVIEWER_MODEL")
        if not reviewer:
            raise ValueError("AA-OFF requires REVIEWER_MODEL for the independent reviewer")
        if not acting_model:
            raise ValueError("AA-OFF requires AGENT_MODEL (or --model) for the acting model")
        if aa_reviewer.canonical_model(reviewer) == aa_reviewer.canonical_model(acting_model):
            raise ValueError("REVIEWER_MODEL must differ from the acting model for AA-OFF")
        return reviewer
    profile = aa_reviewer.off_approval(harness)
    if not profile.verified:
        raise ValueError(f"AA-OFF approval transport {profile.name!r} has not passed live calibration")
    return aa_reviewer.reviewer_config(dot, pick_env, acting_model).model


def collect_env(args: argparse.Namespace, dot: dict[str, str], harness: dict | None = None, *,
                allow_unverified_approval: bool = False) -> dict[str, str]:
    """Collect container variables from explicit settings and the allowlist.

    Prefer profile and process settings, then use CLI
    --model and --base-url as fallbacks. Explicit --pass-env and --env values
    remain available for additional settings.
    """
    dot = runtime_settings(args, dot)
    env: dict[str, str] = {}
    for name in args.pass_env:
        if name not in os.environ:
            log(f"[warn] Requested --pass-env {name} is absent from the host environment")
        elif name not in env:
            env[name] = os.environ[name]
    for name in dict.fromkeys((*AGENT_SETTINGS, *(harness or {}).get("env_allowlist", []))):
        val = pick_env(dot, name)
        if val and name not in env:
            env[name] = val
    # auth_bridge maps existing credentials to native CLI variables, such as
    # ANTHROPIC_AUTH_TOKEN, only when the target has no explicit value.
    for name, value in bridge_env(harness or {}, dot).items():
        if name not in env:
            env[name] = value
    # Harness-specific container settings can point at services exposed by Docker Desktop.
    # Keep them out of the host env allowlist, which would forward loopback addresses verbatim.
    env.update((harness or {}).get("container_env") or {})
    # Resolve model and endpoint from process settings; the CLI provides fallbacks.
    model = selected_model(args, dot, harness)
    if model:
        env["AGENT_MODEL"] = model.split("/")[-1] if (harness or {}).get("id", "codex") == "codex" else model
    # The --base-url fallback sets the container AGENT_BASE_URL.
    if args.base_url and "AGENT_BASE_URL" not in env:
        env["AGENT_BASE_URL"] = args.base_url
    if args.agent_extra_cli:
        env["AGENT_EXTRA"] = " ".join(args.agent_extra_cli)
    for pair in args.env:
        key, _, value = pair.partition("=")
        if not key:
            raise SystemExit(f"Invalid --env (expected KEY=VALUE): {pair!r}")
        env[key] = value
    # The experiment profile wins over inherited/manual environment values.
    if allow_unverified_approval:
        env.update(mechanism_mode_env(
            args, harness, allow_unverified_approval=True))
    else:
        env.update(mechanism_mode_env(args, harness))
    return env


def env_flags(env: dict[str, str]) -> list[str]:
    """Convert environment values into Docker -e KEY=VALUE arguments."""
    result: list[str] = []
    for key, value in env.items():
        result += ["-e", f"{key}={value}"]
    return result


def redact(cmd: list[str]) -> list[str]:
    """Redact secret -e KEY=VALUE arguments before writing console logs."""
    secret_keys = set(AGENT_SETTINGS)
    out: list[str] = []
    i = 0
    while i < len(cmd):
        if cmd[i] == "-e" and i + 1 < len(cmd):
            key = cmd[i + 1].split("=", 1)[0]
            if key in secret_keys or any(part in key.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH")):
                out += [cmd[i], f"{key}=<redacted>"]
            else:
                out += [cmd[i], cmd[i + 1]]
            i += 2
        else:
            out.append(cmd[i])
            i += 1
    return out


def main(argv: list[str] | None = None, *, allow_unverified_approval: bool = False) -> list[Path]:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--harness", required=True, help="Harness ID (configuration under scripts/_shared/harness/, such as codex)")
    ap.add_argument("--mechanism", default=None, help="Mechanism abbreviation (directory under scripts/, such as ni)")
    ap.add_argument("--assume-gemini-pt-configurable", action="store_true",
                    help="Use Gemini PT OFF/ON under an explicit C assumption without changing recorded implementation ratings")
    ap.add_argument("--task", default=None, help="Explicit task directory; overrides mechanism and condition path resolution")
    ap.add_argument("--condition", default=None, help="Task condition within the mechanism, such as clean or attack")
    ap.add_argument("--mode", default=None,
                    help="Mechanism mode: on is strict, off is permissive; inject the harness recipe profile through HARNESS_MECH_ARGS")
    ap.add_argument("--task-id", default=None, help="Base task ID within the mechanism")
    ap.add_argument("--model", default="", help="Agent model name; AGENT_MODEL in the process environment takes precedence; leading /xxx/ prefixes are removed")
    ap.add_argument("--base-url", default="", help="Model service base URL; AGENT_BASE_URL in the process environment takes precedence")
    ap.add_argument("--agent-extra-cli", action="append", default=[], help="Additional agent CLI options (repeatable); defaults retain the native policy")
    ap.add_argument("--agent-home-dir", type=Path, default=None, help="Host directory to copy into the container agent home")
    ap.add_argument("--image", default=None, help="Override the harness image; defaults to the recipe image field")
    ap.add_argument("--workdir", default=None, help="Override the container work directory; native tasks inherit image WORKDIR")
    ap.add_argument("--artifact-path", action="append", default=[], help="Absolute container artifact path (repeatable); defaults to the workspace except /")
    ap.add_argument("--no-artifacts", action="store_true", help="Collect logs only; independent verification retrieves stopped-container artifacts")
    ap.add_argument("--skip-verifiers", action="store_true", help="Run the agent without uploading tests; use external independent verification")
    ap.add_argument("--agent-timeout", type=int, default=28800, help="Agent timeout in seconds; default 28800 (8 hours); 0 disables the limit")
    ap.add_argument("--build-timeout", type=int, default=1800, help="Timeout for same-container verification")
    ap.add_argument("--attempts", "-k", type=int, default=1, help="Number of attempts for the same task")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Result output root directory")
    ap.add_argument("--flat-output", action="store_true",
                    help="Place timestamp directories directly under --out (matrix already supplies trial identity)")
    ap.add_argument("--pass-env", action="append", default=[], help="Host environment variable to forward (repeatable)")
    ap.add_argument("--env", action="append", default=[], help="Literal KEY=VALUE environment setting (repeatable)")
    ap.add_argument("--keep", action="store_true", help="Keep containers after execution and print their names for inspection")
    ap.add_argument(
        "--no-seccomp-unconfined",
        action="store_true",
        help="Omit the default --security-opt seccomp=unconfined. Codex native "
        "bubblewrap requires user namespaces that Docker default seccomp "
        "blocks in the disposable container (EPERM).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print the container script and exit without calling Docker")
    ap.add_argument("--cpus", type=float, help="Container CPU limit")
    ap.add_argument("--memory-mb", type=int, help="Container memory limit in MiB")
    ap.add_argument("--network", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    allowed_modes = ["off", "on", "native"]
    if args.mode is not None and args.mode not in allowed_modes:
        ap.error(f"invalid --mode {args.mode!r}; permitted modes: {allowed_modes}")
    if args.attempts < 1 or args.agent_timeout < 0 or args.build_timeout < 1:
        ap.error("attempts and build-timeout must be positive; agent-timeout must be nonnegative")
    if args.agent_timeout < 0:
        ap.error("--agent-timeout must be non-negative")

    harness = load_harness(args.harness)
    harness_registry.require_executable(harness)
    image = args.image or harness.get("image")
    if not image:
        raise SystemExit(f"Harness {args.harness!r}: neither recipe image nor --image is set")
    # Seed agent home from --agent-home-dir or the harness default configuration.
    agent_home = resolve_agent_home(args, harness)

    task = resolve_task_dir(args)
    app_src = task / "environment" / "app"
    native_environment = (task / "environment" / "Dockerfile").is_file()
    for required in (task / "instruction.md", task / "tests"):
        if not required.exists():
            raise SystemExit(f"Missing task file: {required}")
    if not native_environment and not app_src.is_dir():
        raise SystemExit("Task requires environment/Dockerfile or legacy environment/app")
    if native_environment and not args.image and not args.dry_run:
        raise SystemExit("Build native tasks with docker_builder.py build --task ... --image ..., then select that task-specific image with --image")
    workdir = args.workdir or (None if native_environment else "/app")
    gemini_native_ni = (harness_registry.recipe_id(args.harness) in ("gemini-cli", "qwen") and args.mechanism == "ni"
                        and args.mode in ("off", "on"))
    if gemini_native_ni and (not native_environment or not args.network):
        raise SystemExit("Gemini NI requires a native task image and its per-trial Docker network")
    native_sandbox_paths = gemini_native_sandbox_paths(task) if gemini_native_ni else ()
    for path in [workdir, *args.artifact_path]:
        if path is not None and not path.startswith("/"):
            raise SystemExit(f"Container path must be absolute: {path}")

    approval_profile = None
    legacy_native_reviewer = False
    if args.mechanism == "aa" and args.mode == "off":
        aa_spec = (harness.get("mechanisms") or {}).get("auto_approve_mode") or {}
        legacy_native_reviewer = aa_spec.get("off_reviewer") == "native_independent_ai"
        if not legacy_native_reviewer:
            approval_profile = aa_reviewer.off_approval(harness)
            if not approval_profile.verified and not allow_unverified_approval:
                raise ValueError(
                    f"AA-OFF approval transport {approval_profile.name!r} has not passed live calibration")
    approval_pty = bool(approval_profile and approval_profile.transport == "pty")
    approval_structured = bool(approval_profile and approval_profile.transport != "pty")
    execution_pty = approval_pty or aa_on_requires_pty(args, harness)

    if args.dry_run:
        mechanism_mode_env(args, harness, allow_unverified_approval=allow_unverified_approval)
        # Print the container script for inspection without calling Docker.
        print(build_container_script(harness, Path("."), workdir, args.skip_verifiers,
                                     args.agent_timeout,
                                     interactive=execution_pty,
                                     structured=bool(approval_profile and approval_profile.transport != "pty"),
                                     enforce_timeout=execution_pty and not approval_pty,
                                     external_write_audit=(args.mechanism == "ro"
                                                           and args.harness == "claude-code")), end="")
        if not args.skip_verifiers:
            print(build_verdict_script(), end="")
        return []

    docker_version = check_docker()
    inspected = docker("image", "inspect", image, "--format", "{{json .Config}}")
    if inspected.returncode:
        raise SystemExit(inspected.stderr)
    image_config = json.loads(inspected.stdout)
    identity = docker("image", "inspect", image, "--format", "{{.Id}}")
    if identity.returncode:
        raise SystemExit("Cannot record the exact harness image identity")
    workdir = workdir or image_config.get("WorkingDir") or "/"
    artifact_paths = [] if args.no_artifacts else (args.artifact_path or ([workdir] if workdir != "/" else []))
    # Read allowlisted process credentials and provider settings without printing values.
    dot = runtime_settings(args, load_repo_env())
    env = collect_env(args, dot, harness,
                      allow_unverified_approval=allow_unverified_approval)
    # AA-OFF reviewer configuration and credentials remain host-only. The container receives
    # only the one-shot native answer after its own approval prompt has been observed.
    reviewer = (aa_reviewer.reviewer_config(dot, pick_env, selected_model(args, dot, harness),
                                             agent_timeout=args.agent_timeout)
                if approval_profile is not None else None)
    reviewer_model = (aa_reviewer_model(args, dot, harness, selected_model(args, dot, harness))
                      if legacy_native_reviewer else (reviewer.model if reviewer else None))
    # Native NI allows only the configured model endpoint through its policy proxy.
    # Model APIs otherwise use their original configured URLs directly.
    if env.get("GEMINI_SANDBOX_PROXY_COMMAND"):
        model_host = urlsplit(env.get("GOOGLE_GEMINI_BASE_URL")
                              or "https://generativelanguage.googleapis.com").hostname
        for key in ("NO_PROXY", "no_proxy"):
            values = env.get(key, "").replace(",", " ").split()
            env[key] = ",".join(value for value in values if value.casefold() != (model_host or "").casefold())
        env = configure_gemini_model_proxy(env)
    # Output: <out>/<mechanism-or-adhoc>/<harness>/<condition-or-task>/<timestamp>_a<attempt>/.
    label = args.mode or args.condition or task.name
    out_root = args.out if args.flat_output else args.out / (args.mechanism or "adhoc") / args.harness / label
    out_root.mkdir(parents=True, exist_ok=True)

    rows = []
    manifests = []
    # Each attempt uses a fresh disposable container and complete evaluation.
    for attempt in range(1, args.attempts + 1):
        ts = (_dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
              + f"-{uuid.uuid4().hex[:8]}")
        run_dir = out_root / f"{ts}_a{attempt}"
        (run_dir / "logs" / "agent").mkdir(parents=True, exist_ok=True)
        container = f"benchmark-{args.harness}-{label}-a{attempt}-{ts}"
        workspace_volume = None
        gemini_sandbox_network = None
        trial_workdir = workdir
        console = run_dir / "console.log"
        instruction_bytes = (task / "instruction.md").read_bytes()
        (run_dir / "instruction.md").write_bytes(instruction_bytes)
        console_lines: list[str] = []
        sandbox_support_volume = None
        manifest: dict[str, object] = {
            "runner": "scripts/_shared/run_agent.py",
            "status": "execution_error",
            "mechanism": args.mechanism,
            "harness_id": args.harness,
            "version": harness.get("version"),
            "source_type": harness.get("source_type"),
            "provenance": harness.get("provenance"),
            "image": image,
            "image_id": identity.stdout.strip(),
            "environment_mode": "dockerfile" if native_environment else "legacy-app",
            "workdir": workdir,
            "artifact_paths": artifact_paths,
            "skip_verifiers": args.skip_verifiers,
            "agent_timeout": args.agent_timeout,
            "task": str(task.relative_to(REPO)) if task.is_relative_to(REPO) else str(task),
            "instruction_sha256": hashlib.sha256(instruction_bytes).hexdigest(),
            "condition": args.condition,
            "mode": getattr(args, "mode", None),
            "mechanism_configuration": mechanism_mode_env(
                args, harness, allow_unverified_approval=allow_unverified_approval),
            "model": env.get("AGENT_MODEL", ""),
            "agent_extra_cli": args.agent_extra_cli,
            "agent_home": str(agent_home) if agent_home else None,
            "docker_server_version": docker_version,
            "started_at": ts,
            "env_keys": sorted(env),
            "container": container,
            "agent_started": False,
        }

        def note(cmd: list[str], cp: subprocess.CompletedProcess) -> None:
            # Append the redacted command and captured stdout/stderr to console.log.
            console_lines.append("$ " + " ".join(redact(cmd)))
            if cp.stdout:
                console_lines.append(cp.stdout.rstrip())
            if cp.stderr:
                console_lines.append(cp.stderr.rstrip())
            console.write_text("\n".join(console_lines) + "\n", encoding="utf-8")
            redact_log_file(console, credential_values(dot, harness))

        def run_step(cmd: list[str], what: str, timeout: int | None = 120) -> subprocess.CompletedProcess:
            """Run and log one Docker command; abort this attempt on failure."""
            cp = docker(*cmd, timeout=timeout)
            for secret in credential_values(dot, harness):
                cp.stdout = (cp.stdout or "").replace(secret, "<redacted>")
                cp.stderr = (cp.stderr or "").replace(secret, "<redacted>")
            note(cmd, cp)
            if cp.returncode != 0:
                raise SystemExit(f"[{what}] failed: {cp.stderr.strip()}")
            return cp

        try:
            # 1) Start a sleeping disposable container from the harness image.
            if gemini_native_ni:
                workspace_volume = f"benchmark-gemini-ni-{uuid.uuid4().hex[:12]}"
                if args.mode == "on":
                    sandbox_prefix = "qwen-code" if harness_registry.recipe_id(args.harness) == "qwen" else "gemini-cli"
                    gemini_sandbox_network = f"{sandbox_prefix}-sandbox-{uuid.uuid4().hex[:12]}"
                manifest.update(workspace_volume=workspace_volume,
                                gemini_sandbox_network=gemini_sandbox_network)
                run_step(["volume", "create", workspace_volume], "gemini workspace volume")
                volume_info = run_step(
                    ["volume", "inspect", workspace_volume, "--format", "{{.Mountpoint}}"],
                    "gemini workspace volume mountpoint")
                volume_mountpoint = volume_info.stdout.strip()
                if (not volume_mountpoint.startswith("/") or ":" in volume_mountpoint
                        or "\n" in volume_mountpoint):
                    raise RuntimeError("Docker returned an unsupported Gemini workspace volume mountpoint")
                run_step([
                    "run", "--rm", "--network", "none",
                    "--mount", f"type=volume,source={workspace_volume},target=/benchmark-workspace",
                    "--entrypoint", "/bin/sh", image, "-c",
                    "cp -a /app/. /benchmark-workspace/",
                ], "seed Gemini workspace volume")
                sandbox_support_mountpoint = None
                if native_sandbox_paths:
                    sandbox_support_volume = f"benchmark-gemini-support-{uuid.uuid4().hex[:12]}"
                    manifest["sandbox_support_volume"] = sandbox_support_volume
                    run_step(["volume", "create", sandbox_support_volume],
                             "Gemini sandbox support volume")
                    support_info = run_step(
                        ["volume", "inspect", sandbox_support_volume, "--format", "{{.Mountpoint}}"],
                        "Gemini sandbox support volume mountpoint")
                    sandbox_support_mountpoint = support_info.stdout.strip()
                    if (not sandbox_support_mountpoint.startswith("/")
                            or ":" in sandbox_support_mountpoint
                            or "\n" in sandbox_support_mountpoint):
                        raise RuntimeError("Docker returned an unsupported Gemini support volume mountpoint")
                    seed_lines = ["set -eu"]
                    support_root = PurePosixPath("/benchmark-sandbox-support")
                    for support_path in native_sandbox_paths:
                        path = PurePosixPath(support_path)
                        staged = support_root.joinpath(*path.parts[1:])
                        seed_lines.append(f"mkdir -p {shlex.quote(str(staged.parent))}")
                        seed_lines.append(
                            f"cp -a {shlex.quote(support_path)} {shlex.quote(str(staged))}")
                    run_step([
                        "run", "--rm", "--network", "none",
                        "--mount", f"type=volume,source={sandbox_support_volume},target=/benchmark-sandbox-support",
                        "--entrypoint", "/bin/sh", image, "-c", "\n".join(seed_lines),
                    ], "stage Gemini native sandbox support files")
                # Gemini's file tools validate paths against the process cwd.
                # Keep /app as that cwd because task instructions use /app;
                # the Docker wrapper maps its sandbox mount to this volume.
                trial_workdir = workdir
                sandbox_flags = ["--volume", f"{volume_mountpoint}:/app"]
                if sandbox_support_mountpoint:
                    sandbox_flags += gemini_native_sandbox_mount_flags(
                        sandbox_support_mountpoint, native_sandbox_paths)
                if args.mode == "off":
                    sandbox_flags += ["--network", args.network]
                env["SANDBOX_FLAGS"] = shlex.join(sandbox_flags)
                if harness_registry.recipe_id(args.harness) == "qwen":
                    env["QWEN_SANDBOX_IMAGE"] = image
                    env["QWEN_AGENT_CONTAINER_NAME"] = container
                    if gemini_sandbox_network:
                        env["QWEN_SANDBOX_NETWORK_NAME"] = gemini_sandbox_network
                env["GEMINI_AGENT_CONTAINER_NAME"] = container
                if gemini_sandbox_network:
                    env["GEMINI_SANDBOX_NETWORK_NAME"] = gemini_sandbox_network
                    manifest["env_keys"] = sorted(env)
                manifest.update(
                    workdir=trial_workdir,
                    workspace_volume=workspace_volume,
                    sandbox_support_volume=sandbox_support_volume,
                    sandbox_support_paths=list(native_sandbox_paths),
                    gemini_sandbox_network=gemini_sandbox_network,
                    env_keys=sorted(env),
                )
            docker_run = ["run", "-d", "--name", container]
            if args.network:
                docker_run += ["--network", args.network]
            if gemini_native_ni:
                docker_run += [
                    "--mount", "type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock",
                    "--mount", f"type=volume,source={workspace_volume},target=/app",
                ]
            if args.cpus:
                docker_run += ["--cpus", str(args.cpus)]
            if args.memory_mb:
                docker_run += ["--memory", f"{args.memory_mb}m"]
            namespace_required = harness.get("mechanisms", {}).get("workspace_boundary", {}).get("requires_namespace")
            if args.mechanism:
                active_key = load_mechanism(args.mechanism).get("mechanism_key")
                namespace_required = namespace_required or harness.get("mechanisms", {}).get(active_key, {}).get("requires_namespace")
            if not args.no_seccomp_unconfined and namespace_required:
                # Native bubblewrap sandboxes create a user namespace and mount a new /proc.
                # Docker default seccomp and masked /proc paths can reject initialization.
                # Permit the required namespace operations through seccomp and SYS_ADMIN
                # and remove Docker system-path masking for this outer experiment container.
                # This lets the harness sandbox enforce its own configured boundary
                # instead of measuring a sandbox initialization failure as the ON outcome.
                docker_run += ["--security-opt", "seccomp=unconfined",
                               "--security-opt", "systempaths=unconfined",
                               "--security-opt", "apparmor=unconfined",
                               "--cap-add", "SYS_ADMIN"]
            docker_run += ["--workdir", workdir, *env_flags(env), image, "sleep", "infinity"]
            run_step(docker_run, "docker run")
            # 2) Create destination directories before copying task files.
            run_step(
                ["exec", container, "mkdir", "-p", "/scripts", "/tests", "/logs/agent", "/logs/verifier"],
                "prepare dirs",
            )
            # 3) Copy environment/app and the agent instruction into the container.
            # Keep verifier materials out of the agent workspace until execution ends;
            # the host uploads tests to /tests after step 4.
            if not native_environment:
                run_step(["cp", str(app_src) + "/.", f"{container}:{workdir}"], "copy legacy app")
            run_step(["cp", str(run_dir / "instruction.md"), f"{container}:/scripts/instruction.md"], "copy instruction")

            # Copy optional task-level setup.sh only when it exists.
            setup = task / "setup.sh"
            if setup.exists():
                run_step(["cp", str(setup), f"{container}:/scripts/setup.sh"], "copy setup.sh")

            # Use write_bytes to preserve LF shell scripts on Windows;
            # CRLF scripts cannot execute correctly inside the Linux container.
            (run_dir / "container_run.sh").write_bytes(build_container_script(
                harness, run_dir, trial_workdir, args.skip_verifiers, args.agent_timeout,
                interactive=execution_pty, structured=approval_structured,
                enforce_timeout=execution_pty and not approval_pty,
                external_write_audit=(args.mechanism == "ro"
                                      and args.harness == "claude-code")).encode("utf-8"))
            run_step(["cp", str(run_dir / "container_run.sh"), f"{container}:/scripts/run.sh"], "copy run.sh")

            # Seed agent home from the explicit directory or bundled harness settings.
            if agent_home is not None:
                run_step(["cp", str(stage_context(agent_home)) + "/.", f"{container}:/root/.agent-preload"], "copy agent home")
            if gemini_native_ni and harness_registry.recipe_id(args.harness) == "qwen":
                proxy = REPO / "scripts/ni/qwen-model-proxy.py"
                run_step(["cp", str(stage_context(proxy.parent) / proxy.name), f"{container}:/root/.agent-preload/model-proxy.py"],
                         "install Qwen native model-endpoint proxy")
            if gemini_native_ni:
                wrapper = REPO / "scripts/ni" / (harness_registry.recipe_id(args.harness) + "-docker-wrapper.sh")
                run_step(["cp", str(stage_context(wrapper.parent) / wrapper.name), f"{container}:/usr/local/bin/docker"],
                         "install Gemini per-trial Docker network wrapper")
                run_step(["exec", container, "chmod", "0755", "/usr/local/bin/docker"],
                         "enable Gemini Docker wrapper")
                run_step(["exec", container, "/usr/bin/docker", "version", "--format",
                          "{{.Server.Version}}"], "Gemini Docker backend preflight")

            # 4) Execute the agent through container_run.sh.
            manifest["agent_started"] = True
            # Host deadline covers a stalled or modified in-container timeout command.
            deadline = args.agent_timeout + 120 if args.skip_verifiers and args.agent_timeout else None
            try:
                if execution_pty:
                    # Allocate the terminal inside the container. This keeps the host bridge
                    # on terminal bytes only, while reviewer context and credentials remain
                    # outside the container.
                    pty_shim = ("import os,pty,sys; s=pty.spawn(sys.argv[1:]); "
                                "raise SystemExit(os.waitstatus_to_exitcode(s))")
                    cmd = ["exec", "-i", container, "python3", "-c", pty_shim,
                           "bash", "/scripts/run.sh"]
                else:
                    cmd = (["exec", "-i"] if reviewer_model else ["exec"])
                    cmd += [container, "bash", "/scripts/run.sh"]
                note(cmd, subprocess.CompletedProcess(cmd, 0, "Streaming agent output to logs/agent/agent.log", ""))
                # Direct file descriptors avoid communicate() buffering and work even
                # for partial lines. No host directory is exposed to the agent.
                if approval_profile is not None:
                    assert reviewer is not None
                    decision_log = run_dir / "aa-review-decisions.jsonl"
                    common = dict(
                        config=reviewer, task_goal=instruction_bytes.decode("utf-8", errors="replace"),
                        harness_id=args.harness, harness_version=harness.get("version"),
                        mechanism="auto_approve_mode", trace_path=run_dir / "logs/agent/agent.log",
                        decisions_path=decision_log, timeout=deadline, cwd=REPO,
                        risk_metadata={"aa_mode": "off", "workdir": workdir,
                                       "native_profile": mechanism_mode_env(
                                           args, harness,
                                           allow_unverified_approval=allow_unverified_approval)},
                        extra_secrets=tuple(value for key, value in env.items()
                                            if any(part in key.upper() for part in
                                                   ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH"))))
                    if approval_pty:
                        assert approval_profile.driver is not None
                        cp, review_summary = aa_reviewer.run_session(
                            ["docker", *cmd], driver=approval_profile.driver, **common)
                    else:
                        cp, review_summary = aa_reviewer.run_structured_session(
                            ["docker", *cmd], transport=approval_profile.transport,
                            diagnostics_path=run_dir / "runner.log",
                            approval_timeout_sec=aa_reviewer.approval_timeout(
                                {**dot, **os.environ}, args.agent_timeout),
                            actor_model=selected_model(args, dot, harness),
                            **common)
                    manifest["aa_review"] = {
                        **review_summary,
                        "log": str(decision_log.relative_to(run_dir)),
                        "sha256": aa_reviewer.decision_log_sha256(decision_log),
                    }
                else:
                    with (run_dir / "logs/agent/agent.log").open("wb", buffering=0) as trace, \
                            (run_dir / "runner.log").open("wb", buffering=0) as diagnostics:
                        private_input = ((reviewer_model + "\n").encode("utf-8")
                                         if reviewer_model else None)
                        cp = run_bounded(["docker", *cmd], input=private_input,
                                         stdout=trace, stderr=diagnostics, timeout=deadline)
                if cp.returncode:
                    failure_log = (run_dir / "logs/agent/agent.log" if approval_profile is not None
                                   else run_dir / "runner.log")
                    raise SystemExit(f"[run agent + verifiers] failed ({cp.returncode}); see {failure_log}")
            except subprocess.TimeoutExpired:
                manifest["host_timeout"] = True
                if approval_profile is not None:
                    decision_log = run_dir / "aa-review-decisions.jsonl"
                    review_summary = aa_reviewer.summarize_decision_log(
                        decision_log, approval_profile.name, timeout=True)
                    manifest["aa_review"] = {
                        **review_summary,
                        "log": str(decision_log.relative_to(run_dir)),
                        "sha256": (aa_reviewer.decision_log_sha256(decision_log)
                                   if decision_log.is_file() else None),
                    }
                log(f"[timeout] {container}: host deadline reached; freezing and preserving partial evidence")

            # 4b) Upload tests and verdict.sh after the agent exits, then run verifiers.
            # Skip this step for --skip-verifiers; independent verification runs separately.
            if not args.skip_verifiers:
                # The trailing /. copies tests directory contents into /tests;
                # omitting it would nest the directory at /tests/tests.
                run_step(["cp", str(stage_context(task / "tests")) + "/.", f"{container}:/tests"],
                         "copy tests after the agent phase")
                (run_dir / "verdict.sh").write_bytes(build_verdict_script().encode("utf-8"))
                run_step(["cp", str(run_dir / "verdict.sh"), f"{container}:/scripts/verdict.sh"],
                         "copy verdict.sh")
                verdict_cmd = ["docker", "exec", container, "bash", "/scripts/verdict.sh"]
                note(verdict_cmd, subprocess.CompletedProcess(verdict_cmd, 0, "", ""))
                with (run_dir / "runner.log").open("ab", buffering=0) as diagnostics:
                    cp_verdict = run_bounded(verdict_cmd, stdout=diagnostics, stderr=diagnostics,
                                             timeout=args.build_timeout)
                if cp_verdict.returncode:
                    raise SystemExit(
                        f"[run verifier] failed ({cp_verdict.returncode}); see {run_dir / 'runner.log'}")

            # 5) Retrieve results and workspace artifacts from the container.
            if gemini_native_ni:
                frozen = docker("stop", container + "-sandbox", timeout=30)
                note(["stop", container + "-sandbox"], frozen)
                absent = "no such container" in (frozen.stderr or "").lower()
                if frozen.returncode and not absent:
                    raise RuntimeError("Cannot freeze the nested NI sandbox before snapshots")
                manifest["native_sandbox_stopped"] = True
            run_step(["stop", container], "freeze endpoint before collecting any artifacts")
            manifest["container_stopped"] = True
            run_step(["cp", f"{container}:/logs/.", str(run_dir / "logs")], "copy logs")
            artifact_map = {}
            for index, path in enumerate(artifact_paths):
                dest = run_dir / ("app" if path == "/app" else f"artifacts/{index}")
                dest.parent.mkdir(parents=True, exist_ok=True)
                run_step(["cp", f"{container}:{path}", str(dest)], f"copy {path}")
                artifact_map[path] = str(dest.relative_to(run_dir))
            manifest["artifacts"] = artifact_map

            # 6) Read utility reward.txt and security boundary.json verdicts.
            reward_txt = run_dir / "logs" / "verifier" / "reward.txt"
            boundary_json = run_dir / "logs" / "verifier" / "boundary.json"
            reward = reward_txt.read_text().strip() if reward_txt.exists() else (
                "deferred_to_offline_verifier" if args.skip_verifiers else "missing")
            boundary: dict[str, object] = {}
            if boundary_json.exists():
                try:
                    boundary = json.loads(boundary_json.read_text(encoding="utf-8"))
                except Exception:
                    pass
            manifest["reward"] = reward
            exit_file = run_dir / "logs/agent/exit_code.txt"
            manifest["agent_exit_code"] = "124" if manifest.get("host_timeout") else (
                exit_file.read_text().strip() if exit_file.exists() else None)
            if (approval_pty and manifest["agent_exit_code"] in ("124", "137")
                    and not (manifest.get("aa_review") or {}).get("events")
                    and not (manifest.get("aa_review") or {}).get("fail_closed")):
                decision_log = run_dir / "aa-review-decisions.jsonl"
                secret_values = tuple(value for key, value in env.items()
                                      if any(part in key.upper() for part in
                                             ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH")))
                aa_reviewer.append_uncertain_session(
                    decision_log, driver=approval_profile.name,
                    task_goal=instruction_bytes.decode("utf-8", errors="replace"),
                    harness_id=args.harness, harness_version=harness.get("version"),
                    mechanism="auto_approve_mode",
                    transcript_path=run_dir / "logs/agent/agent.log",
                    secrets=((reviewer.api_key,) if reviewer else ()) + secret_values,
                    risk_metadata={"aa_mode": "off", "workdir": workdir,
                                   "native_profile": mechanism_mode_env(
                                       args, harness,
                                       allow_unverified_approval=allow_unverified_approval)},
                    reason=f"agent exited {manifest['agent_exit_code']}; PTY state is uncertain",
                )
                review_summary = aa_reviewer.summarize_decision_log(
                    decision_log, approval_profile.name, timeout=True)
                manifest["aa_review"] = {
                    **review_summary,
                    "log": str(decision_log.relative_to(run_dir)),
                    "sha256": aa_reviewer.decision_log_sha256(decision_log),
                }
            manifest["boundary"] = boundary
            rows.append((attempt, reward, boundary.get("boundary_landed"), boundary.get("change"), str(run_dir)))
            manifest["status"] = "completed"
        finally:
            manifest.setdefault("token_usage", token_telemetry(
                run_dir / "logs/agent/agent.log", harness.get("trace_format", "unsupported")))
            # Session histories are evidence, not task artifacts. Capture even
            # when --no-artifacts is used or the native CLI exits with an error.
            if harness.get("native_trace_paths") and manifest.get("agent_started"):
                try:
                    if not manifest.get("container_stopped"):
                        stopped = docker("stop", container, timeout=30)
                        manifest["container_stopped"] = stopped.returncode == 0
                    manifest["native_traces"] = []
                    for index, source in enumerate(harness["native_trace_paths"]):
                        dest = run_dir / "logs" / "native" / str(index)
                        dest.mkdir(parents=True, exist_ok=True)
                        captured = docker("cp", f"{container}:{source}/.", str(dest), timeout=120)
                        manifest["native_traces"].append({"source": source,
                            "path": str(dest.relative_to(run_dir)), "exit_code": captured.returncode})
                except (OSError, subprocess.TimeoutExpired) as error:
                    manifest["native_trace_error"] = type(error).__name__
            if not args.keep:
                docker("rm", "-f", container)
                errors = cleanup_native_sandbox(
                    manifest, lambda arguments, label: docker(*arguments, timeout=60))
                if errors:
                    manifest.setdefault("cleanup_errors", []).extend(errors)
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            secrets = tuple(dict.fromkeys((
                *credential_values(dot, harness),
                *(value for key, value in env.items()
                  if any(part in key.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH"))),
                *((reviewer.api_key,) if reviewer else ()))))
            for path in (console, run_dir / "runner.log", *(run_dir / "logs").rglob("*")):
                redact_log_file(path, secrets)
            manifests.append(run_dir / "manifest.json")
            # Remove the container after each attempt, unless --keep requests inspection.
            if args.keep:
                log(f"[keep] Container retained: {container}")

        log(f"[attempt {attempt}] reward={rows[-1][1]} boundary_landed={rows[-1][2]} change={rows[-1][3]}")
        log(f"  out: {run_dir}")

    print("\nsummary: attempt | reward | boundary_landed | change | out_dir")
    for row in rows:
        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
    return manifests


def write_report(path: Path, report: dict) -> None:
    """Checkpoint on the host, including failures; never write results into a dataset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def checked_archive(path: Path) -> list[tarfile.TarInfo]:
    """Accept regular files/directories only for transfer into a clean verifier.

    Security snapshots may contain links and are interpreted by an oracle without
    extraction. Utility archives cannot carry links, devices, or traversal paths.
    """
    with tarfile.open(path) as archive:
        members = archive.getmembers()
    names = set()
    for member in members:
        name = PurePosixPath(member.name)
        if (name.is_absolute() or ".." in name.parts or "\\" in member.name
                or not (member.isfile() or member.isdir()) or name in names):
            raise ValueError(f"Unsafe or ambiguous utility archive entry: {member.name!r}")
        names.add(name)
    return members


def trace_artifact_inspection(log_path: Path, artifact: str) -> bool | None:
    """Return True only for conservative positive evidence that an artifact was read."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    escaped = re.escape(artifact)
    readers = r"(?:cat|sed|head|tail|less|more|rg|grep|Get-Content|read_text|open)"
    return True if re.search(rf"{readers}[^\n]{{0,240}}{escaped}|{escaped}[^\n]{{0,240}}{readers}",
                             text, re.IGNORECASE) else None


def native_project_startup_refusal(harness_id: str, exit_code: str, log_path: Path) -> bool:
    """Recognize the pinned Gemini trust guard, independently of task success."""
    if harness_id != "gemini-cli" or str(exit_code) != "55":
        return False
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "Gemini CLI is not running in a trusted directory." in text


class BenchmarkCommands:
    """Bounded Docker commands and binary snapshots with per-attempt logs."""

    def __init__(self, directory: Path, secrets: tuple[str, ...] = ()):
        self.directory = directory
        self.secrets = secrets
        directory.mkdir(parents=True, exist_ok=True)

    def run(self, cmd: list[str], name: str, timeout: int = 120, check: bool = True,
            stdout_path: Path | None = None, stdin_path: Path | None = None):
        import contextlib
        log(f"[{name}] {' '.join(redact(cmd))}")
        log_path = self.directory / f"{name}.log"
        try:
            with contextlib.ExitStack() as stack:
                live_log = stack.enter_context(log_path.open("wb"))
                output = stack.enter_context(stdout_path.open("wb")) if stdout_path else live_log
                source = stack.enter_context(stdin_path.open("rb")) if stdin_path else None
                try:
                    cp = run_bounded(cmd, cwd=REPO, stdin=source, stdout=output,
                                     stderr=live_log, timeout=timeout)
                except subprocess.TimeoutExpired as error:
                    live_log.write(f"\nTimeout after {timeout}s; command tree terminated\n".encode())
                    raise RuntimeError(f"{name}: timeout after {timeout}s") from error
        finally:
            redact_log_file(log_path, self.secrets)
        content = log_path.read_text(encoding="utf-8", errors="replace")
        stdout, stderr = ("", content) if stdout_path or cp.returncode else (content, "")
        if check and cp.returncode:
            raise RuntimeError(f"{name}: exit {cp.returncode}; see {self.directory / (name + '.log')}")
        return subprocess.CompletedProcess(cmd, cp.returncode, stdout, stderr)


def verify_artifacts(commands: BenchmarkCommands, container: str, image: str,
                     spec: dict, workspace: str, row: dict) -> None:
    """Transfer declared outputs and immutable-path final-state inputs to an offline verifier."""
    limits = spec["verifier"].get("environment", {})
    flags = []
    if limits.get("cpus"):
        flags += ["--cpus", str(limits["cpus"])]
    if limits.get("memory_mb"):
        flags += ["--memory", f"{limits['memory_mb']}m"]
    commands.run(["docker", "run", "-d", "--network", "none", "--name", container,
                  *flags, image, "sleep", "infinity"], "verifier-create")
    # Windows checkouts can contain CRLF shell scripts. Every verifier already
    # requires bash to run /tests/test.sh, but not every verifier image has Python.
    # Normalize only the clean verifier's shell transport bytes; source snapshots
    # and test logic stay intact.
    normalize = "shopt -s nullglob globstar; for path in /tests/**/*.sh; do sed -i 's/\\r$//' \"$path\"; done"
    commands.run(["docker", "exec", container, "bash", "-c", normalize], "verifier-shell-newlines")
    # ``artifacts`` are agent-writable files under the workspace.  A task may
    # additionally declare ``verifier_inputs`` for final state living outside
    # that workspace (for example a service-owned database mutated through an
    # MCP server).  Both are copied only after the agent has stopped.
    transfers = [("artifact", artifact) for artifact in spec["artifacts"]]
    transfers.extend(("verifier-input", path) for path in spec.get("verifier_inputs", []))
    for index, (kind, artifact) in enumerate(transfers):
        destination = PurePosixPath(artifact)
        if kind == "artifact":
            destination.relative_to(PurePosixPath(workspace))
        snapshot = commands.directory / f"{kind}-{index}.tar"
        capture = commands.run(["docker", "cp", f"{row['container']}:{destination}", "-"],
                               f"{kind}-{index}-capture", stdout_path=snapshot, check=False)
        if capture.returncode:
            # Docker's missing-path error is an absent solution, not a transport error.
            if "Could not find the file" in capture.stderr or "no such file or directory" in capture.stderr:
                row.setdefault("missing_artifacts" if kind == "artifact" else "missing_verifier_inputs", []).append(str(destination))
                snapshot.unlink(missing_ok=True)
                continue
            raise RuntimeError(f"Cannot capture utility artifact: {destination}")
        members = checked_archive(snapshot)
        if not members or any(PurePosixPath(m.name).parts[0] != destination.name for m in members):
            raise ValueError(f"Unexpected archive root for {destination}")
        parent = str(destination.parent)
        commands.run(["docker", "exec", container, "mkdir", "-p", parent], f"{kind}-{index}-mkdir")
        commands.run(["docker", "cp", "-", f"{container}:{parent}"],
                     f"{kind}-{index}-transfer", stdin_path=snapshot)
    commands.run(["docker", "exec", container, "mkdir", "-p", "/logs/verifier"], "verifier-logs")
    if spec["verifier"].get("final_answer_utility"):
        trace_path = row.get("_final_answer_trace_path")
        trace_format = row.get("_final_answer_trace_format")
        if not trace_path or not trace_format:
            raise ValueError("final-answer utility requires a native trace and format")
        from final_answer import extract_final_answer
        answer = extract_final_answer(Path(trace_path), trace_format)
        row["final_answer_extraction"] = "found" if answer is not None else "missing"
        answer_path = commands.directory / "final-answer.json"
        answer_path.write_text(json.dumps({"text": answer or ""}, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        commands.run(["docker", "cp", str(answer_path),
                      f"{container}:/logs/verifier/final_answer.json"], "verifier-answer")
        verifier_answer_path = commands.directory / "verifier-final-answer.json"
        commands.run(["docker", "exec", container, "cat", "/logs/verifier/final_answer.json"],
                     "capture-verifier-answer", stdout_path=verifier_answer_path)
        archived_sha256 = hashlib.sha256(answer_path.read_bytes()).hexdigest()
        verifier_sha256 = hashlib.sha256(verifier_answer_path.read_bytes()).hexdigest()
        row["final_answer_handoff"] = {
            "archived_path": answer_path.name,
            "verifier_input_path": verifier_answer_path.name,
            "archived_sha256": archived_sha256,
            "verifier_input_sha256": verifier_sha256,
            "matches": archived_sha256 == verifier_sha256,
        }
        if archived_sha256 != verifier_sha256:
            raise ValueError("verifier received a different final answer than the archived answer")
    result = commands.run(["docker", "exec", container, "bash", "/tests/test.sh"],
                          "utility", int(spec["verifier"]["timeout_sec"]) + 60, check=False)
    reward = commands.run(["docker", "exec", container, "cat", "/logs/verifier/reward.txt"],
                          "reward", check=False)
    components = commands.run(["docker", "exec", container, "cat",
                               "/logs/verifier/utility_subtasks.json"],
                              "utility-subtasks", check=False)
    ctrf = commands.run(["docker", "exec", container, "cat", "/logs/verifier/ctrf.json"],
                        "utility-ctrf", check=False)
    row["verifier_exit_code"] = result.returncode
    row["offline_utility_passed"] = (bool(int(reward.stdout.strip()))
                                     if reward.returncode == 0 and reward.stdout.strip() in ("0", "1")
                                     else None)
    try:
        if not components.returncode:
            payload = json.loads(components.stdout)
            row["verifier_utility_subtasks"] = validate_subtasks(payload.get("subtasks"), "utility")
        elif not ctrf.returncode:
            row["verifier_utility_subtasks"] = utility_subtasks_from_ctrf(
                json.loads(ctrf.stdout), row["offline_utility_passed"])
        else:
            raise ValueError("verifier emitted neither utility_subtasks.json nor ctrf.json")
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid utility sub-task report: {error}") from error


def benchmark_main(mechanism: str, dataset: Path, oracle, argv: list[str] | None = None) -> dict:
    """Reusable paired benchmark driver. The only mechanism-specific code is oracle(case, archives).

    Manifest contract: version, modes, cases[{task_id, workspace, snapshots}].
    Each task supplies native environment/Dockerfile, tests/Dockerfile, task.toml.
    New mechanisms reuse this function; they do not copy container orchestration.
    """
    parser = argparse.ArgumentParser(description=f"Run the full {mechanism} benchmark with independent oracles.")
    parser.add_argument("--dataset", type=Path, default=dataset)
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument("--modes", nargs="+", choices=["off", "on", "native"])
    parser.add_argument("--harness", default="codex")
    parser.add_argument("--assume-gemini-pt-configurable", action="store_true",
                        help="Use Gemini PT OFF/ON under an explicit C assumption without changing recorded implementation ratings")
    parser.add_argument("--no-markdown", action="store_true", help="Write machine-readable experiment results only")
    parser.add_argument("--attempts", "-k", type=int, default=1)
    parser.add_argument("--agent-timeout", type=int, default=28800,
                        help="Agent wall-clock budget in seconds (default 28800, 8 hours)")
    parser.add_argument("--jobs", type=int, default=0,
                        help="Concurrent trials (default 0: one per attempt when attempts > 1, else serial). "
                             "Each trial gets its own container; not part of the fingerprint, so a batch can be resumed with a different value")
    parser.add_argument("--build-timeout", type=int, default=1800)
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--agent-extra-cli", action="append", default=[])
    parser.add_argument("--agent-home-dir", type=Path)
    parser.add_argument("--no-seccomp-unconfined", action="store_true")
    parser.add_argument("--out", type=Path, help="Unique report directory; use --resume to reuse")
    parser.add_argument("--resume", action="store_true",
                        help="Skip completed rows; a strictly larger --attempts appends new attempts after configuration verification")
    parser.add_argument("--skip-build", action="store_true", help="Use the content-tagged images from an earlier build")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the entire matrix without Docker/API calls")
    args = parser.parse_args(argv)
    if args.attempts < 1 or args.build_timeout < 1 or (args.agent_timeout is not None and args.agent_timeout < 1):
        parser.error("attempts and timeouts must be positive")
    if args.jobs < 0:
        parser.error("--jobs must be non-negative")
    if args.resume and not args.out:
        parser.error("--resume requires --out")
    dataset = args.dataset.resolve()
    validate_suite(mechanism, dataset)
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    cases = {case["task_id"]: case for case in manifest["cases"]}
    if len(cases) != len(manifest["cases"]):
        parser.error("Duplicate task IDs in manifest")
    selected = args.tasks or list(cases)
    modes = args.modes or manifest["modes"]
    if (len(set(selected)) != len(selected) or len(set(modes)) != len(modes)
            or set(selected) - cases.keys()
            or set(modes) - (set(manifest["modes"]) | {"native"})):
        parser.error("Unknown or duplicate tasks/modes")
    dot = runtime_settings(args, load_repo_env())
    harness = load_harness(args.harness)
    mode_policy = None
    from native_profiles import native_toggle_policy
    mode_policy = native_toggle_policy(harness, mechanism, args.modes,
                                      assume_gemini_pt_configurable=args.assume_gemini_pt_configurable)
    modes = mode_policy["modes"] if mode_policy["status"] == "ready" else []
    reviewer_model = None
    reviewer_endpoint_sha256 = None
    if mechanism == "aa" and "off" in modes:
        acting_model = selected_model(args, dot, harness)
        reviewer_model = pick_env(dot, "REVIEWER_MODEL")
        reviewer_base_url = pick_env(dot, "REVIEWER_BASE_URL") or pick_env(dot, "AGENT_BASE_URL")
        if not acting_model:
            parser.error("AA-OFF requires AGENT_MODEL (or --model) for the acting model")
        if not reviewer_model:
            parser.error("AA-OFF requires REVIEWER_MODEL for the independent reviewer")
        if aa_reviewer.canonical_model(reviewer_model) == aa_reviewer.canonical_model(acting_model):
            parser.error("REVIEWER_MODEL must differ from the acting model for AA-OFF")
        if reviewer_base_url:
            reviewer_endpoint_sha256 = hashlib.sha256(reviewer_base_url.encode()).hexdigest()
    # Content fingerprint includes dataset, implementation and harness configuration, never API keys.
    digest = hashlib.sha256((dataset / "manifest.json").read_bytes())
    roots = [dataset / "tasks", HARNESS_DIR / harness_registry.recipe_id(args.harness), MECH_DIR / mechanism]
    if harness.get("build_recipe"):
        roots.append(HERE / "harness" / "_shared")
    if args.agent_home_dir:
        roots.append(args.agent_home_dir.resolve())
    for root in roots:
        if not root.is_dir():
            parser.error(f"Missing input directory: {root}")
        for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(path.relative_to(root).as_posix().encode())
                digest.update(path.read_bytes())
    for path in (HERE / "run_agent.py", REPO / "scripts/aa/aa_reviewer.py", HERE / "docker_builder.py", HERE / "metrics.py",
                 HERE / "process_utils.py", HERE / "package_validation.py", HERE / "harness_registry.py", HERE / "trace_formats.py",
                 HERE / "study.py", HERE / "mech_common.py", HERE / "native_profiles.py",
                 HERE / "native_profiles.json", HERE / "subtask_metrics.py", HERE / "final_answer.py"):
        digest.update(path.read_bytes())
    config = {"mechanism": mechanism, "dataset_version": manifest["version"], "harness": harness,
              "tasks": selected, "modes": modes, "mode_policy": mode_policy, "attempts": args.attempts,
              "agent_timeout": args.agent_timeout, "model": selected_model(args, dot, harness) or "native-default",
              "endpoint_sha256": hashlib.sha256((pick_env(dot, "AGENT_BASE_URL") or args.base_url).encode()).hexdigest(),
              "agent_extra_cli": args.agent_extra_cli, "seccomp_unconfined": not args.no_seccomp_unconfined,
              "inputs_sha256": digest.hexdigest()}
    if args.no_markdown:
        config["write_markdown"] = False
    if reviewer_model:
        config["reviewer_model"] = reviewer_model.split("/")[-1]
    if reviewer_endpoint_sha256:
        config["reviewer_endpoint_sha256"] = reviewer_endpoint_sha256
    config["native_configuration_sha256"] = hashlib.sha256(json.dumps({
        "allowlisted": {
            name: pick_env(dot, name)
            for name in harness.get("env_allowlist", [])
            if any(part in name for part in ("BASE_URL", "MODEL", "HOST"))
        },
        "container_env": harness.get("container_env", {}),
    }, sort_keys=True).encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    plan = []
    specs = {}
    for task_id in selected:
        case = cases[task_id]
        workspace = PurePosixPath(case["workspace"])
        if not workspace.is_absolute() or ".." in workspace.parts or str(workspace) == "/":
            parser.error(f"Invalid workspace: {workspace}")
        for snap in case["snapshots"]:
            if not PurePosixPath(snap).is_absolute() or ".." in PurePosixPath(snap).parts:
                parser.error(f"Invalid snapshot path: {snap}")
        task = dataset / "tasks" / f"{task_id}-attack"
        for required in ("environment/Dockerfile", "tests/Dockerfile", "tests/test.sh", "instruction.md", "task.toml"):
            if not (task / required).is_file():
                parser.error(f"Missing {task / required}")
        spec = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
        for artifact in spec["artifacts"]:
            path = PurePosixPath(artifact)
            if ".." in path.parts or not path.is_relative_to(workspace):
                parser.error(f"Artifact must be within workspace: {artifact}")
        for verifier_input in spec.get("verifier_inputs", []):
            path = PurePosixPath(verifier_input)
            if not path.is_absolute() or ".." in path.parts or path == PurePosixPath("/"):
                parser.error(f"Verifier input must be a specific absolute path: {verifier_input}")
        timeout = args.agent_timeout or int(spec["agent"]["timeout_sec"])
        if timeout <= 0:
            parser.error(f"Invalid native agent timeout: {task_id}")
        specs[task_id] = spec
        for mode in modes:
            for attempt in range(1, args.attempts + 1):
                plan.append({"harness_id": harness_registry.canonical_id(args.harness),
                             "model": config["model"], "profile_id": fingerprint,
                             "task_id": task_id, "mode": mode, "attempt": attempt,
                             "agent_timeout_sec": timeout, "surface": case.get("surface"),
                             "attack_method": case.get("attack_method")})
    if args.dry_run:
        result = {"fingerprint": fingerprint, "config": config, "planned_runs": plan,
                  "status": mode_policy["status"] if mode_policy and mode_policy["status"] != "ready" else "planned"}
        if mode_policy and mode_policy["status"] != "ready":
            print(mode_policy["reason"])
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    if mode_policy and mode_policy["status"] != "ready":
        result = {"schema_version": 4, "fingerprint": fingerprint, "config": config,
                  "status": mode_policy["status"], "error": mode_policy["reason"],
                  "planned_runs": 0, "runs": []}
        if args.out:
            out = args.out.resolve()
            if out.exists() and any(out.iterdir()):
                raise ValueError("Blocked-profile output must be empty; use a new output directory")
            out.mkdir(parents=True, exist_ok=True)
            report_metrics(result, out, quiet=True)
            write_report(out / "report.json", result)
        print(mode_policy["reason"])
        return result
    harness_registry.require_executable(harness)
    if harness.get("auth_home_required") and not args.agent_home_dir:
        raise SystemExit(f"{args.harness}: cached login required; use --agent-home-dir with an isolated authenticated home")
    auth = harness.get("auth_any", [])
    bridged = bridge_env(harness, dot)
    if bridged:
        log(f"[env] auth_bridge derived: {', '.join(sorted(bridged))} (from process environment)")
    if auth and not any(pick_env(dot, name) or name in bridged for name in auth) and not args.agent_home_dir:
        raise SystemExit(
            f"{args.harness}: missing authentication; configure one of {', '.join(auth)}, "
            f"add an auth_bridge entry to harness/{args.harness}/harness.json, or use --agent-home-dir"
        )
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")
    out = (args.out or DEFAULT_OUT / mechanism / f"{args.harness}-{stamp}").resolve()
    report_path = out / "report.json"
    relation = None
    if args.resume:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        relation = resume_config_relation(report.get("config", {}), config)
        if relation is None:
            parser.error("Resume fingerprint differs; use a new output directory")
        if relation == "extension":
            previous_attempts = report["config"]["attempts"]
            extension = {
                "from_attempts": previous_attempts,
                "to_attempts": args.attempts,
                "previous_fingerprint": report["fingerprint"],
                "extended_at": stamp,
            }
            previous_modes = report["config"].get("modes")
            if previous_modes != config.get("modes"):
                extension.update({
                    "from_modes": previous_modes,
                    "to_modes": config.get("modes"),
                    "mode_change": "additive",
                })
            report["resume_extensions"] = [*(report.get("resume_extensions") or []), extension]
            report["fingerprint"] = fingerprint
            report["config"] = config
            report["planned_runs"] = len(plan)
    else:
        if out.exists() and any(out.iterdir()):
            parser.error("Output directory is nonempty; choose another or use --resume")
        report = {"schema_version": 4, "status": "running", "fingerprint": fingerprint, "config": config,
                  "created_at": stamp, "planned_runs": len(plan), "runs": []}
    if mechanism == "pif" and args.resume:
        report["status"] = "running"
        report.pop("measurement_status", None)
    write_report(report_path, report)
    secrets = credential_values(dot, harness)
    commands = BenchmarkCommands(out / "build", secrets)
    try:
        commands.run(["docker", "version", "--format", "{{.Server.Version}}"], "preflight", 60)
    except (OSError, RuntimeError) as error:
        report.update(status="blocked_environment", error=str(error))
        report_metrics(report, out)
        write_report(report_path, report)
        print(json.dumps({"report": str(report_path), "status": report["status"]}))
        return report
    built = set()
    # Parallelize independent attempts by default because provider latency dominates runtime.
    # Use --jobs to override concurrency; jobs=1 executes attempts sequentially.
    jobs = args.jobs or max(1, args.attempts)
    report_lock = threading.Lock()
    build_locks: dict[str, threading.Lock] = {}
    locks_guard = threading.Lock()

    def publish() -> None:
        """Serialize report flushing: concurrent trials share one report file."""
        with report_lock:
            write_report(report_path, report)

    def build_lock(image_tag: str) -> threading.Lock:
        """One builder per image tag: concurrent trials share a single build."""
        with locks_guard:
            return build_locks.setdefault(image_tag, threading.Lock())

    def run_trial(planned: dict) -> None:
        key = (planned["task_id"], planned["mode"], planned["attempt"])
        previous = next((r for r in reversed(report["runs"]) if (r["task_id"], r["mode"], r["attempt"]) == key), None)
        if previous and previous["status"] == "completed":
            return
        task_id, mode, attempt = key
        # Attack task only; mode (off/on) changes the harness boundary config, not the task.
        task = dataset / "tasks" / f"{task_id}-attack"
        token = uuid.uuid4().hex[:12]
        trial_canary = f"{mechanism}-{uuid.uuid4().hex}" if mechanism in ("ni", "pt") else None
        image = f"benchmark-{mechanism}-{task_id}-{args.harness}:{fingerprint[:12]}"
        verifier_image = f"benchmark-{mechanism}-{task_id}-verifier:{fingerprint[:12]}"
        sidecar_specs = cases[task_id].get("sidecars") or []
        if not sidecar_specs and cases[task_id].get("sidecar"):
            sidecar_specs = [{"id": "service", **cases[task_id]["sidecar"]}]
        sidecar_images = {
            spec["id"]: f"benchmark-{mechanism}-{task_id}-{spec['id']}:{fingerprint[:12]}"
            for spec in sidecar_specs
        }
        directory = out / f"{task_id}-{mode}-a{attempt}-{token}"
        trial = BenchmarkCommands(directory, secrets)
        row = {**planned, "status": "running", "agent_started": False, "utility": None,
               "boundary_landed": None, "attacker_success": None,
               "output": str(directory.relative_to(out)), "image": image}
        with report_lock:
            report["runs"].append(row)
            write_report(report_path, report)
        verifier = f"benchmark-verify-{token}"
        network = f"session-{token}" if sidecar_specs else None
        sidecar_containers = {spec["id"]: f"{spec['id']}-{token}" for spec in sidecar_specs}
        container = None
        agent = None
        phase = "build"
        trial_started = stage_started = time.monotonic()
        row["started_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
        def checkpoint(stage):
            nonlocal stage_started
            now = time.monotonic()
            if row.get("phase"):
                row.setdefault("phase_durations_sec", {})[row["phase"]] = round(now - stage_started, 3)
            stage_started = now
            row.update(phase=stage, phase_started_at=_dt.datetime.now(_dt.timezone.utc).isoformat())
            with report_lock:
                report["updated_at"] = row["phase_started_at"]
                write_report(report_path, report)
        try:
            checkpoint(phase)
            if not args.skip_build:
                runtime_image = harness.get("image")
                if (harness.get("task_dockerfile") or harness.get("build_recipe") == "shared") and runtime_image:
                    with build_lock(runtime_image):
                        if runtime_image not in built:
                            runtime_probe = commands.run(
                                ["docker", "image", "inspect", runtime_image],
                                f"{args.harness}-runtime-image", 60, check=False)
                            if runtime_probe.returncode:
                                commands.run([sys.executable, str(HERE / "docker_builder.py"), "build", args.harness],
                                             f"{args.harness}-runtime", args.build_timeout)
                            built.add(runtime_image)
                with build_lock(verifier_image):
                    if verifier_image not in built:
                        verifier_build = ["docker", "build", "-t", verifier_image,
                                          str(stage_context(task / "tests"))]
                        commands.run(verifier_build,
                                     f"{task_id}-verifier", args.build_timeout)
                        built.add(verifier_image)
                with build_lock(image):
                    if image not in built:
                        image_probe = commands.run(
                            ["docker", "image", "inspect", image],
                            f"{task_id}-{mode}-image", 60, check=False)
                        if image_probe.returncode:
                            commands.run([sys.executable, str(HERE / "docker_builder.py"), "build", args.harness,
                                          "--task", str(task), "--image", image],
                                         f"{task_id}-{mode}", args.build_timeout)
                        built.add(image)
                for sidecar_spec in sidecar_specs:
                    sidecar_image = sidecar_images[sidecar_spec["id"]]
                    with build_lock(sidecar_image):
                        if sidecar_image not in built:
                            context = stage_context(task / sidecar_spec["build_context"])
                            commands.run(["docker", "build", "-t", sidecar_image, str(context)],
                                         f"{task_id}-{sidecar_spec['id']}", args.build_timeout)
                            built.add(sidecar_image)
            phase = "agent"
            checkpoint(phase)
            if sidecar_specs:
                trial.run(["docker", "network", "create", "--driver", "bridge", network],
                          "network-create")
                for sidecar_spec in sidecar_specs:
                    sidecar_id = sidecar_spec["id"]
                    sidecar = sidecar_containers[sidecar_id]
                    sidecar_options = ["docker", "run", "-d", "--name", sidecar,
                                       "--network", network]
                    if trial_canary and sidecar_spec.get("receives_trial_canary"):
                        sidecar_options += ["--env", f"NI_TRIAL_CANARY={trial_canary}"]
                    sidecar_options += ["--network-alias", sidecar_spec["network_alias"],
                                        sidecar_images[sidecar_id]]
                    trial.run(sidecar_options, f"{sidecar_id}-create")
                    health_url = sidecar_spec.get("health_url", "http://127.0.0.1:8080/health")
                    ready = ("import time,urllib.request\n"
                             "for attempt in range(50):\n"
                             " try:\n"
                             f"  urllib.request.urlopen({health_url!r},timeout=1).read(); break\n"
                             " except OSError:\n"
                             "  time.sleep(.1)\n"
                             "else:\n"
                             " raise SystemExit('sidecar did not become ready')")
                    trial.run(["docker", "exec", sidecar, "python", "-c", ready],
                              f"{sidecar_id}-ready", 15)
            options = ["--harness", args.harness, "--mechanism", mechanism, "--mode", mode, "--task", str(task),
                       "--image", image, "--out", str(directory / "agent"), "--flat-output", "--keep", "--skip-verifiers",
                       "--workdir", cases[task_id]["workspace"],
                       "--agent-timeout", str(planned["agent_timeout_sec"]), "--model", args.model, "--base-url", args.base_url]
            if args.assume_gemini_pt_configurable:
                options.append("--assume-gemini-pt-configurable")
            if network:
                options += ["--network", network]
            if trial_canary:
                ticket_variable = "WORKSHOP_TICKET" if mechanism == "pt" else "NI_TRIAL_CANARY"
                options += ["--env", f"{ticket_variable}={trial_canary}"]
            if mechanism == "pt":
                options += ["--env", f"PT_TASK_ID={task_id}",
                            "--artifact-path", cases[task_id]["workspace"],
                            "--artifact-path", "/var/spool/pt"]
            for extra in args.agent_extra_cli:
                options.append(f"--agent-extra-cli={extra}")
            if args.agent_home_dir:
                options += ["--agent-home-dir", str(args.agent_home_dir)]
            if args.no_seccomp_unconfined:
                options.append("--no-seccomp-unconfined")
            limits = specs[task_id].get("environment", {})
            for field, flag in (("cpus", "--cpus"), ("memory_mb", "--memory-mb")):
                if limits.get(field):
                    options += [flag, str(limits[field])]
            paths = main(options)
            agent = json.loads(paths[0].read_text(encoding="utf-8"))
            container = agent["container"]
            row.update(container=container, agent_started=agent["agent_started"],
                       agent_exit_code=agent["agent_exit_code"], agent_manifest=str(paths[0].relative_to(out)),
                       image_id=agent.get("image_id"))
            row["token_usage"] = agent.get("token_usage", {
                "status": "not_reported", "source": "native_trace",
                "reason": "legacy_manifest_without_token_telemetry"})
            if isinstance(agent.get("aa_review"), dict):
                row["aa_review"] = agent["aa_review"]
            trace_path = paths[0].parent / "logs/agent/agent.log"
            if trace_path.is_file():
                row.update(provider_diagnostics(trace_path))
            if not agent.get("container_stopped"):
                raise RuntimeError("Agent container must be stopped before snapshots")
            phase = "security"
            checkpoint(phase)
            snapshots = {}
            try:
                for index, source in enumerate(cases[task_id]["snapshots"]):
                    archive = directory / f"security-{index}.tar"
                    snapshot_container = container
                    snapshot_source = source
                    for sidecar_spec in sidecar_specs:
                        if source in sidecar_spec["snapshots"]:
                            snapshot_container = sidecar_containers[sidecar_spec["id"]]
                            snapshot_source = sidecar_spec["snapshots"][source]
                            break
                    trial.run(["docker", "cp", f"{snapshot_container}:{snapshot_source}", "-"],
                              f"security-{index}", stdout_path=archive)
                    snapshots[source] = archive
                row.update(oracle(cases[task_id], snapshots))
                if mechanism == "ro" and args.harness == "claude-code":
                    from ro import write_audit
                    audit_targets = cases[task_id].get("write_audit", {}).get("targets", [])
                    if not audit_targets:
                        raise ValueError(f"RO task {task_id} has no protected-path write-audit targets")
                    runner_log = paths[0].parent / "runner.log"
                    host_trace = runner_log.read_text(encoding="utf-8", errors="replace")
                    trace_text = write_audit.extract_trace(host_trace)
                    write_events = write_audit.parse_trace(trace_text, audit_targets)
                    journal = directory / "protected-write-events.jsonl"
                    journal.write_text(write_audit.jsonl(write_events), encoding="utf-8", newline="\n")
                    row.update(write_audit.attach_events(row, write_events))
                    row["protected_write_audit"] = {
                        "status": "measured",
                        "host_journal": journal.name,
                        "sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
                        "event_count": len(write_events),
                        "allowed_event_count": sum(event["allowed"] for event in write_events),
                        "denied_event_count": sum(not event["allowed"] for event in write_events),
                    }
            except (OSError, RuntimeError, ValueError, tarfile.TarError) as error:
                row["security_error"] = str(error)
                if cases[task_id].get("oracle_engine") == "pif_state":
                    row.update(boundary_landed=None, attacker_success=None,
                               oracles=[{"id": spec["id"], "security_violation": None,
                                         "error": "endpoint_snapshot_unavailable"}
                                        for spec in cases[task_id]["oracles"]])
                elif mechanism == "ro" and args.harness == "claude-code":
                    row.update(boundary_landed=None, attacker_success=None,
                               protected_write_landed=None,
                               protected_write_goal_persisted=None,
                               protected_write_rolled_back=None,
                               write_audit_status="unknown")
            phase = "verifier"
            checkpoint(phase)
            if specs[task_id]["verifier"].get("final_answer_utility"):
                row["_final_answer_trace_path"] = str(trace_path)
                row["_final_answer_trace_format"] = harness.get("trace_format", "unsupported")
            try:
                verify_artifacts(trial, verifier, verifier_image, specs[task_id],
                                 cases[task_id]["workspace"], row)
            finally:
                row.pop("_final_answer_trace_path", None)
                row.pop("_final_answer_trace_format", None)
            row["release_validation_passed"] = row.get("offline_utility_passed") is True
            attach_trial_scores(row, row["verifier_utility_subtasks"],
                                cases[task_id].get("subtask_oracles"))
            # Mirror the pooled host-side utility into the run manifest; under
            # --skip-verifiers it was only "deferred_to_offline_verifier".
            try:
                _manifest = json.loads(paths[0].read_text(encoding="utf-8"))
                _manifest["reward"] = (str(row["utility"]) if row["utility"] is not None
                                       else "deferred_to_offline_verifier")
                paths[0].write_text(json.dumps(_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            except (OSError, ValueError, TypeError):
                pass
            row["security_measurement_status"] = "measured" if row["boundary_landed"] is not None else "unknown"
            pif_endpoint_unknown = (cases[task_id].get("oracle_engine") == "pif_state"
                                    and row.get("oracles") and row["boundary_landed"] is None)
            row["status"] = "completed" if row["task_utility"]["value"] is not None and (row["boundary_landed"] is not None or pif_endpoint_unknown) else "verifier_error"
            if row["agent_exit_code"] != "0":
                if mechanism == "pt" and native_project_startup_refusal(
                        args.harness, row["agent_exit_code"], trace_path):
                    row["agent_outcome"] = "native_startup_refusal"
                else:
                    row["status"] = "agent_timeout" if row["agent_exit_code"] == "124" else "agent_error"
            artifact_spec = next((s for s in sidecar_specs if s.get("artifact_path")), None)
            if artifact_spec:
                row["artifact_inspected"] = trace_artifact_inspection(
                    paths[0].parent / "logs/agent/agent.log", artifact_spec["artifact_path"])
        except KeyboardInterrupt:
            row.update(status="interrupted", error=f"Interrupted during {phase}")
            with report_lock:
                report["status"] = "interrupted"
            raise
        except (OSError, RuntimeError, ValueError, tarfile.TarError, subprocess.TimeoutExpired, SystemExit) as error:
            row.update(status=f"{phase}_error", error=str(error))
        finally:
            row.setdefault("phase_durations_sec", {})[row.get("phase", phase)] = round(time.monotonic() - stage_started, 3)
            row["duration_sec"] = round(time.monotonic() - trial_started, 3)
            row["finished_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
            if container is None:
                partial = list((directory / "agent").rglob("manifest.json"))
                if partial:
                    agent = json.loads(partial[0].read_text(encoding="utf-8"))
                    container = agent.get("container")
                    row["agent_started"] = agent.get("agent_started", False)
                    row["token_usage"] = agent.get("token_usage", {
                        "status": "not_reported", "source": "native_trace",
                        "reason": "legacy_manifest_without_token_telemetry"})
            row.setdefault("token_usage", {"status": "not_reported", "source": "native_trace",
                                           "reason": "agent_trace_unavailable"})
            for name in filter(None, (container, verifier, *sidecar_containers.values())):
                try:
                    trial.run(["docker", "rm", "-f", name], f"cleanup-{name}", 60, check=False)
                except (OSError, RuntimeError) as error:
                    row.setdefault("cleanup_errors", []).append(str(error))
            if agent:
                errors = cleanup_native_sandbox(
                    agent, lambda arguments, label: trial.run(
                        ["docker", *arguments], label, 60, check=False))
                if errors:
                    row.setdefault("cleanup_errors", []).extend(errors)
            if network:
                try:
                    trial.run(["docker", "network", "rm", network], "cleanup-network", 60, check=False)
                except (OSError, RuntimeError) as error:
                    row.setdefault("cleanup_errors", []).append(str(error))
            publish()

    try:
        if jobs == 1:
            for planned in plan:
                run_trial(planned)
        else:
            log(f"[jobs] {jobs} parallel jobs; {len(plan)} trials")
            with futures.ThreadPoolExecutor(max_workers=jobs) as pool:
                pending = [pool.submit(copy_context().run, run_trial, planned) for planned in plan]
                for future in futures.as_completed(pending):
                    future.result()
    except KeyboardInterrupt:
        # In-flight trials clean up after themselves; record the batch state and stop scheduling.
        report["status"] = "interrupted"
        write_report(report_path, report)
        raise
    # Trials finish in any order under --jobs; list them in plan order like the serial path
    # (stable, so re-run rows for one key keep their relative order for the latest-row lookup).
    order = {(p["task_id"], p["mode"], p["attempt"]): index for index, p in enumerate(plan)}
    report["runs"].sort(key=lambda row: order.get((row["task_id"], row["mode"], row["attempt"]), len(plan)))
    latest = {(r["task_id"], r["mode"], r["attempt"]): r for r in report["runs"]}
    report["status"] = "completed" if len(latest) == len(plan) and all(r["status"] == "completed" for r in latest.values()) else "incomplete"
    report.pop("error", None)
    report["summary"] = {"planned": len(plan), "completed": sum(r["status"] == "completed" for r in latest.values()),
                         "security_observed": sum(r["boundary_landed"] is not None for r in latest.values())}
    report_metrics(report, out)
    write_report(report_path, report)
    print_trial_details(report, out)
    print(json.dumps({"report": str(report_path), "status": report["status"],
                      "measurement_status": report["measurement_status"], "summary": report["summary"]}))
    return report


if __name__ == "__main__":
    main()
