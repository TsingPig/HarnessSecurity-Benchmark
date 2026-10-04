#!/usr/bin/env python3
"""Enable the same native catalog MCP server in both PIF modes."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path


def patch_structured_kwargs():
    executable = shutil.which("gptme")
    if not executable:
        raise RuntimeError("gptme executable not found")
    entrypoint = Path(executable).resolve()
    shebang = entrypoint.read_text(encoding="utf-8").splitlines()[0]
    if not shebang.startswith("#!"):
        raise RuntimeError("gptme entrypoint has no Python shebang")
    command = shlex.split(shebang[2:].strip())
    interpreter = command[0]
    if Path(interpreter).name == "env":
        interpreter = shutil.which(next(part for part in command[1:] if not part.startswith("-"))) or ""
    probe = subprocess.run([interpreter, "-c", "import gptme, pathlib; print(pathlib.Path(gptme.__file__).parent)"],
                           check=False, capture_output=True, text=True)
    if probe.returncode or not probe.stdout.strip():
        raise RuntimeError("cannot locate gptme package")
    adapter = Path(probe.stdout.strip()) / "tools" / "mcp_adapter.py"
    source = adapter.read_text(encoding="utf-8")
    marker = "# RQ2 MCP kwargs compatibility v1"
    if marker in source:
        return
    before = ('        if not code:\n'
              '            yield Message("system", "No parameters provided")\n'
              '            return\n')
    after = ('        # RQ2 MCP kwargs compatibility v1: structured calls populate kwargs.\n'
             '        if code is None and kwargs is not None:\n'
             '            code = json.dumps(kwargs)\n'
             '        if not code:\n'
             '            yield Message("system", "No parameters provided")\n'
             '            return\n')
    if before not in source:
        raise RuntimeError(f"unsupported installed MCP adapter layout: {adapter}")
    adapter.write_text(source.replace(before, after, 1), encoding="utf-8")


def main():
    adapter = os.environ.get("MCP_ADAPTER")
    server = {"command": "python3", "args": ["/usr/local/bin/pif-mcp-server"]}
    if adapter == "copilot":
        config = {"mcpServers": {"catalog": {
            "type": "local", **server, "tools": ["*"],
        }}}
        Path("/scripts/copilot-pif-mcp.json").write_text(
            json.dumps(config) + "\n", encoding="utf-8")
        return
    if adapter == "claude":
        Path("/scripts/pif-mcp.json").write_text(
            json.dumps({"mcpServers": {"catalog": server}}) + "\n", encoding="utf-8")
        return
    if adapter == "gemini":
        trusted = Path("/root/.gemini/trustedFolders.json")
        trusted.parent.mkdir(parents=True, exist_ok=True)
        trusted.write_text(json.dumps({"/app": "TRUST_FOLDER"}) + "\n", encoding="utf-8")
        Path("/scripts/gemini-pif-settings.json").write_text(
            json.dumps({"mcpServers": {"catalog": {**server, "trust": True}}}) + "\n",
            encoding="utf-8")
        return
    if adapter in ("codex", "qwen"):
        return  # Their native launch profiles configure the same catalog server.
    if adapter != "gptme":
        raise SystemExit(f"Unsupported PIF MCP adapter: {adapter!r}")
    config = Path("/root/.config/gptme/config.toml")
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        '[mcp]\nenabled = true\nauto_start = true\n'
        '[[mcp.servers]]\nname = "catalog"\ncommand = "python3"\n'
        'args = ["/usr/local/bin/pif-mcp-server"]\n', encoding="utf-8")
    patch_structured_kwargs()


if __name__ == "__main__":
    main()
