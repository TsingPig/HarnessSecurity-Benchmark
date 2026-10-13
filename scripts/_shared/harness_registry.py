"""Load the six pinned harness recipes distributed with this benchmark."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ALIASES = {"codex-cli": "codex", "qwen-code": "qwen"}
HARNESS_IDS = ("codex-cli", "claude-code", "copilot-agent", "gemini-cli", "gptme", "qwen-code")


def canonical_id(value):
    return {recipe: identity for identity, recipe in ALIASES.items()}.get(value, value)


def recipe_id(value):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise ValueError(f"Invalid harness ID: {value!r}")
    return ALIASES.get(value, value)


def load(value, root=None):
    if canonical_id(value) not in HARNESS_IDS:
        raise ValueError(f"Unknown harness: {value}")
    path = (Path(root) if root is not None else HERE / "harness") / recipe_id(value) / "harness.json"
    if not path.is_file():
        raise ValueError(f"Missing harness recipe: {value}")
    return json.loads(path.read_text(encoding="utf-8"))


def population():
    return [{"id": identity} for identity in HARNESS_IDS]


def validate(selected=None):
    wanted = set(HARNESS_IDS) if selected is None else {canonical_id(value) for value in selected}
    if wanted - set(HARNESS_IDS):
        raise ValueError(f"Unknown harness selection: {sorted(wanted - set(HARNESS_IDS))}")
    rows = []
    for identity in HARNESS_IDS:
        if identity not in wanted:
            continue
        meta = load(identity)
        if canonical_id(meta["id"]) != identity:
            raise ValueError(f"Recipe identity mismatch: {identity}")
        require_executable(meta)
        if meta.get("agent_home"):
            home = HERE / "harness" / recipe_id(identity) / meta["agent_home"]
            if not home.is_dir():
                raise ValueError(f"Missing bundled harness home: {home}")
        rows.append({"harness_id": identity, "recipe_id": recipe_id(identity),
                     "entrypoint": meta.get("entrypoint", "cli"), "recipe_available": True,
                     "runtime_verified": False, "blockers": []})
    return rows


def require_executable(meta):
    if not meta.get("run_command") or not meta.get("image"):
        raise ValueError(f"{meta['id']}: executable recipe is incomplete")
