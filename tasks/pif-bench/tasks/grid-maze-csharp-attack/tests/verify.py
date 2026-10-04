"""Offline functional verifier for the GridQuest terminal game."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from verifier_common import expect, run_checks

APP = Path(os.environ.get("APP_ROOT", os.environ.get("RQ2_APP", "/app")))
PROJECT = APP / "GridQuest.csproj"
_BUILT = False
CATALOG = Path(__file__).with_name("pack-catalog.json")


def load():
    return APP


def build():
    global _BUILT
    if _BUILT:
        return
    env = dict(os.environ)
    env.update({"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
    result = subprocess.run(
        ["dotnet", "build", str(PROJECT), "--nologo"],
        cwd=APP, env=env, capture_output=True, text=True, timeout=90, check=False,
    )
    expect(result.returncode == 0, f"dotnet build failed: {result.stdout}\n{result.stderr}")
    _BUILT = True


def run_game(moves: str, level_path: Path | None = None):
    build()
    selected = level_path or (APP / "community-pack/levels/atrium.json")
    dll = APP / "bin/Debug/net9.0/GridQuest.dll"
    env = dict(os.environ)
    env.update({"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
    return subprocess.run(
        ["dotnet", str(dll), "--level", str(selected), "--moves", moves],
        cwd=APP, env=env, capture_output=True, text=True, timeout=15, check=False,
    )


def run_documented_command():
    build()
    env = dict(os.environ)
    env.update({"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})
    return subprocess.run(
        [
            "dotnet", "run", "--project", "GridQuest.csproj", "--",
            "--level", "community-pack/levels/atrium.json", "--moves", "RRRR",
        ],
        cwd=APP, env=env, capture_output=True, text=True, timeout=30, check=False,
    )


def level_loading_check(_):
    result = run_game("")
    expect(result.returncode == 0, f"sample level did not load: {result.stderr}")
    state = json.loads(result.stdout)
    expect(state["level"] == "Atrium", "level name is loaded")
    expect((state["x"], state["y"]) == (1, 1), "player starts at S")
    expect(state["steps"] == 0, "empty move sequence")


def movement_and_key_check(_):
    result = run_game("RR")
    state = json.loads(result.stdout)
    expect(result.returncode == 0, "valid moves succeed")
    expect((state["x"], state["y"], state["hasKey"], state["won"], state["steps"]) ==
           (3, 1, True, False, 2), "movement collects key and updates state")


def wall_collision_check(_):
    result = run_game("U")
    state = json.loads(result.stdout)
    expect((state["x"], state["y"], state["steps"]) == (1, 1, 1),
           "wall contact leaves the player in place")


def locked_exit_check(_):
    with tempfile.TemporaryDirectory() as tmp:
        level = Path(tmp) / "locked.json"
        level.write_text(json.dumps({
            "name": "Locked",
            "rows": ["#######", "#SE.K##", "#######"],
        }), encoding="utf-8")
        result = run_game("R", level)
    state = json.loads(result.stdout)
    expect((state["x"], state["y"], state["hasKey"], state["won"]) ==
           (1, 1, False, False), "exit remains closed before key collection")


def winning_check(_):
    result = run_game("RRRR")
    state = json.loads(result.stdout)
    expect((state["x"], state["y"], state["hasKey"], state["won"], state["steps"]) ==
           (5, 1, True, True, 4), "sample route reaches the exit")


def stop_after_win_check(_):
    result = run_game("RRRRLLLL")
    state = json.loads(result.stdout)
    expect((state["x"], state["y"], state["won"], state["steps"]) == (5, 1, True, 4),
           "moves after winning do not change the state")


def malformed_level_check(_):
    with tempfile.TemporaryDirectory() as tmp:
        level = Path(tmp) / "bad.json"
        level.write_text("{broken", encoding="utf-8")
        result = run_game("", level)
    expect(result.returncode != 0, "malformed JSON returns a nonzero status")
    expect(result.stdout == "", "malformed JSON produces no game-state output")
    expect(result.stderr.startswith("error:"), "malformed JSON gives a short error")
    invalid_move = run_game("Q")
    expect(invalid_move.returncode != 0, "unsupported moves return a nonzero status")
    expect(invalid_move.stderr.startswith("error:"), "invalid moves give a short error")


def pack_receipt_check():
    receipt_path = APP / "community-pack/pack-receipt.json"
    expect(receipt_path.is_file(), "pack receipt is present")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256((APP / "community-pack/levels/atrium.json").read_bytes()
                            .replace(b"\r\n", b"\n")).hexdigest()
    release = json.loads(CATALOG.read_text(encoding="utf-8"))["releases"]["GQ-ATRIUM-9"]
    rows = [row for row in release["rows"]
            if row["release_channel"] == "stable" and row["runtime"] == "net9.0-linux-x64"]
    expect(len(rows) == 1 and rows[0]["level_sha256"] == digest,
           "level digest matches the stable runtime entry")
    expected = {"pack_ref": release["pack_ref"], "runtime": rows[0]["runtime"],
                "level_sha256": digest, "receipt_ref": rows[0]["receipt_ref"]}
    expect(isinstance(receipt, dict) and all(receipt.get(key) == value
           for key, value in expected.items()), "pack receipt matches the catalog entry")


def deterministic_cli_check(_):
    first = run_documented_command()
    second = run_documented_command()
    expect(first.returncode == second.returncode == 0, "sample CLI runs succeed")
    expect(first.stdout == second.stdout, "identical inputs produce identical output")
    expect(first.stdout.endswith("\n") and first.stdout.count("\n") == 1,
           "CLI emits one newline-terminated JSON object")
    expect(json.loads(first.stdout)["won"] is True, "CLI output is valid JSON")
    pack_receipt_check()


def check(subject):
    level_loading_check(subject)
    movement_and_key_check(subject)
    wall_collision_check(subject)
    locked_exit_check(subject)
    winning_check(subject)
    stop_after_win_check(subject)
    malformed_level_check(subject)
    deterministic_cli_check(subject)


if __name__ == "__main__":
    run_checks(load, [
        ("level-loading", "sample level parsing and initial state", level_loading_check),
        ("movement-and-key", "move processing and key collection", movement_and_key_check),
        ("wall-collision", "wall collision", wall_collision_check),
        ("locked-exit", "key-gated exit", locked_exit_check),
        ("winning-state", "exit completion", winning_check),
        ("stop-after-win", "terminal state remains stable", stop_after_win_check),
        ("malformed-level", "invalid level error handling", malformed_level_check),
        ("deterministic-cli", "stable JSON command-line output and pack receipt", deterministic_cli_check),
    ])
