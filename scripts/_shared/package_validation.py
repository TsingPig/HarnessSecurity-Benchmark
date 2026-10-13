"""Validate the frozen published tasks without rebuilding authored task sources."""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import tomllib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
RELEASES = {
    "cal": ("cal-v5", 2, "e3185bffa85691d073094415b6ca150ee73f75e390119b01c8ffdbbdd9772d99"),
    "cdl": ("cdl-v5", 2, "501b58dfaeadec366b6502de4348eb36f507869f04a4e872853cc14de3378095"),
    "pr": ("fsb-v1", 4, "4d8aa481d284a1bce703e80999e8ac2cce5c2c2d298b9e8f014f41c6ea93598b"),
    "ni": ("ni-v4", 2, "b79e8b75cfa320bdae21d9a13d9693d7eb6a4f8c9ab1a9c7cce440fd8c85d5e2"),
    "ro": ("ro-neutral-write-journal-v2-20260928", 2, "9f30fe286c089bfadf19da868a48455763edf7f2b3e075e149ca33039266dcf8"),
    "pif": ("pif-v20", 2, "9258ddc3b777aa90ddf0972e5a4406511d91eb41d89a9f8bebb6c9cab8dee8b0"),
    "mcp": ("mcp-v6", 3, "932c46b0ec9ca3ef914c156ef2e8a4c39ffd0a1e379bbce20bb2359b1e884e44"),
    "aa": ("aa-v6", 2, "739fbde0449b578df6fe70434d91e9266840801d011c8503ef018a75beaea052"),
    "pt": ("pt-v2", 4, "582bc217f9db0e959db920776712405b529fb29e5944ebbb72e5f9827bb720f4"),
}
MECHANISM_KEYS = {
    "cal": "command_allowlist", "cdl": "command_denylist", "pr": "path_restriction",
    "ni": "network_isolation", "ro": "readonly_mode", "pif": "prompt_injection_filter",
    "mcp": "mcp_permission", "aa": "auto_approve_mode", "pt": "project_trust",
}
# These two reviewer documents are outside all container build contexts.
# Environment README files remain covered, including attack-bearing carriers.
EDITABLE_DOCUMENTS = {
    "tasks/mvcc-lsm-compaction-attack/README.md",
    "tasks/embedding-drift-monitor-attack/README.md",
}


def repository_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if b"\0" not in data:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            data = data.replace(b"\r\n", b"\n")
    return data


def release_digest(suite: Path, mechanism: str) -> str:
    """Hash the manifest and task filenames/content, with canonical text line endings."""
    paths = [suite / "manifest.json", *(p for p in (suite / "tasks").rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")]
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.relative_to(suite).as_posix()):
        relative = path.relative_to(suite).as_posix()
        if mechanism == "pr" and relative in EDITABLE_DOCUMENTS:
            continue
        digest.update(relative.encode("utf-8") + b"\0"
                      + hashlib.sha256(repository_bytes(path)).digest() + b"\0")
    return digest.hexdigest()


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    _require(bool(value) and not path.is_absolute() and ".." not in path.parts,
             f"Invalid task-relative path: {value}")
    return path


def _absolute_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    _require(path.is_absolute() and path != PurePosixPath("/") and ".." not in path.parts,
             f"Invalid container path: {value}")
    return path


def _check_docker_context(context: Path) -> None:
    dockerfile = context / "Dockerfile"
    _require(dockerfile.is_file(), f"Missing Dockerfile: {context}")
    text = dockerfile.read_text(encoding="utf-8").replace("\\\n", " ")
    for line in text.splitlines():
        match = re.match(r"\s*(?:COPY|ADD)\s+(.*)", line, re.IGNORECASE)
        if not match:
            continue
        rest = match.group(1).strip()
        if re.search(r"(?:^|\s)--from(?:=|\s)", rest):
            continue
        rest = re.sub(r"^--\S+\s+", "", rest)
        operands = json.loads(rest) if rest.startswith("[") else shlex.split(rest)
        for source in operands[:-1]:
            if source.startswith(("http://", "https://")):
                continue
            source = source.lstrip("/")
            _relative_path(source)
            matches = list(context.glob(source)) if any(c in source for c in "*?[") else [context / source]
            _require(bool(matches) and all(path.exists() for path in matches),
                     f"Docker COPY input missing: {dockerfile} -> {source}")


def _check_oracles(case: dict) -> None:
    engine = case["oracle_engine"]
    _require(engine in {"fs", "event", "sqlite", "pif_state"}, f"Unknown oracle engine: {engine}")
    oracles = case["oracles"]
    ids = [oracle["id"] for oracle in oracles]
    _require(bool(ids) and len(ids) == len(set(ids)), f"Missing or duplicate oracles: {case['task_id']}")
    for oracle in oracles:
        _require(oracle["snapshot"] in case["snapshots"], f"Oracle snapshot is not captured: {oracle['id']}")
        if engine == "fs":
            _require(oracle["baseline"] != oracle["goal"], f"Non-discriminating oracle: {oracle['id']}")
        elif engine == "event":
            _relative_path(oracle["evidence_path"])
            _require(bool(oracle["component"]) and bool(oracle["forbidden_actions"]), f"Incomplete event oracle: {oracle['id']}")
        elif engine == "sqlite":
            _relative_path(oracle["database"])
            _require(bool(oracle["success_query"]), f"Missing SQLite oracle query: {oracle['id']}")
        else:
            _relative_path(oracle["state_path"])
            if oracle.get("event_log_path"):
                _relative_path(oracle["event_log_path"])
                _require(isinstance(oracle["baseline_state"], dict) and bool(oracle["forbidden_actions"]),
                         f"Incomplete PIF oracle: {oracle['id']}")
            else:
                _require(isinstance(oracle["expected_state"], dict), f"Missing PIF expected state: {oracle['id']}")


def _check_task(task: Path, case: dict, mechanism_key: str) -> None:
    for relative in ("instruction.md", "task.toml", "attack.json", "tests/test.sh"):
        _require((task / relative).is_file(), f"Missing task file: {task / relative}")
    _require(bool((task / "instruction.md").read_text(encoding="utf-8").strip()), f"Empty instruction: {task}")
    spec = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
    workspace = _absolute_path(case["workspace"])
    for artifact in spec["artifacts"]:
        _require(_absolute_path(artifact).is_relative_to(workspace), f"Artifact outside workspace: {artifact}")
    for section in ("agent", "verifier"):
        _require(spec[section]["timeout_sec"] > 0, f"Invalid {section} timeout: {task}")
    for snapshot in case["snapshots"]:
        _absolute_path(snapshot)
    for kind in ("utility", "attack"):
        items = case["subtask_oracles"][kind]
        ids = [item["id"] for item in items]
        _require(bool(ids) and len(ids) == len(set(ids)), f"Missing or duplicate {kind} sub-task IDs: {task}")
    meta = json.loads((task / "attack.json").read_text(encoding="utf-8"))
    _require(meta["mechanism"] == mechanism_key and meta["condition"] == "attack"
             and meta.get("payload_condition", meta["condition"]) == "attack", f"Invalid attack metadata: {task}")
    for key in ("task_id", "workspace", "surface", "attack_method", "snapshots", "oracle_engine",
                "oracles", "subtask_oracles", "condition_overlays"):
        _require(meta.get(key) == case.get(key), f"Manifest and attack metadata differ: {task} -> {key}")
    _check_oracles(case)
    contexts = {"environment", "tests"}
    sidecars = case.get("sidecars") or ([case["sidecar"]] if case.get("sidecar") else [])
    for sidecar in sidecars:
        context = _relative_path(sidecar["build_context"]).as_posix()
        contexts.add(context)
    for context in sorted(contexts):
        _check_docker_context(task / context)


def validate_suite(mechanism: str, dataset: Path | None = None) -> dict:
    """Validate a released suite; dataset is optional for isolated validation tests."""
    _require(mechanism in RELEASES, f"Unknown mechanism: {mechanism}")
    suite = Path(dataset) if dataset is not None else ROOT / "tasks" / f"{mechanism}-bench"
    manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    version, count, expected = RELEASES[mechanism]
    cases = manifest["cases"]
    ids = [case["task_id"] for case in cases]
    _require(manifest["version"] == version and manifest["base_tasks"] == count == len(cases),
             f"Unexpected release version or task count: {suite}")
    _require(len(ids) == len(set(ids)) and all(re.fullmatch(r"[a-z0-9][a-z0-9-]*", task_id) for task_id in ids),
             f"Invalid or duplicate task IDs: {suite}")
    _require(manifest["mechanism"] == MECHANISM_KEYS[mechanism] and manifest["modes"] == ["off", "on"],
             f"Unexpected mechanism or native modes: {suite}")
    directories = {path.name for path in (suite / "tasks").iterdir() if path.is_dir() and path.name != "__pycache__"}
    _require(directories == {f"{task_id}-attack" for task_id in ids}, f"Task directory population differs: {suite}")
    for case in cases:
        _check_task(suite / "tasks" / f"{case['task_id']}-attack", case, manifest["mechanism"])
    digest = release_digest(suite, mechanism)
    _require(digest == expected, f"Published task files or manifest differ from {version}: {suite}")
    return {"mechanism": mechanism, "dataset_version": version, "base_tasks": count,
            "status": "validated", "sha256": digest}
