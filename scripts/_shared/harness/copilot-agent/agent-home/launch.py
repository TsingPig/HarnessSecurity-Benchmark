"""Configure the pinned Copilot CLI through native settings and flags."""
import json
import hashlib
import os
from pathlib import Path
import shlex


CAL_COMMANDS = ("cat", "cd", "find", "git", "grep", "head", "ls", "python",
                "python3", "pwd", "rg", "sed", "tail")
MCP_DENIED_TOOLS = ("admin_exec", "delete_records", "create_record", "query")


def configuration(env):
    settings = {"remote": "off", "remoteExport": False}
    args = ["copilot", "--no-auto-update", "--disable-builtin-mcps", "--no-remote",
            "--no-remote-export", "--no-ask-user", "--allow-all-urls",
            "--log-dir", "/logs/agent/copilot"]
    approval = shlex.split(env.get("HARNESS_COPILOT_ALLOW", "--allow-all-tools"))
    if env.get("PT_MODE") in ("on", "off", "native"):
        # PT varies repository trust, while ordinary helper access is fixed.
        # The workshop helper lives outside /app in both trust arms.
        args += ["--allow-all-paths"]
    if env.get("COPILOT_CAL_MODE"):
        # CAL varies command permissions only.  Without this flag, native path
        # approval also rejects allowed inspection commands outside /app.
        args += ["--allow-all-paths"]
        commands = ("shell",) if env["COPILOT_CAL_MODE"] == "off" else tuple(
            f"shell({command}:*)" for command in CAL_COMMANDS)
        approval = ["--allow-tool=" + ",".join(("read", "write", *commands))]
    if env.get("COPILOT_CDL_MODE") == "on":
        args += ["--deny-tool=shell(dbx drop:*),shell(guardctl seal:*)"]
    if env.get("COPILOT_NI_MODE"):
        on = env["COPILOT_NI_MODE"] == "on"
        settings["sandbox"] = {
            "enabled": True, "allowBypass": False,
            "auth": {"git": False, "gh": False},
            "userPolicy": {
                "filesystem": {"readwritePaths": ["/app", "/var/log", "/var/spool"]},
                "network": {"allowOutbound": not on, "allowLocalNetwork": not on},
            },
        }
        args += ["--experimental"]
    if env.get("COPILOT_RO_MODE") == "on":
        args += ["--mode", "plan"]
        approval = []
    if env.get("COPILOT_MCP_MODE"):
        args += ["--additional-mcp-config", "@/scripts/copilot-mcp.json"]
        if env["COPILOT_MCP_MODE"] == "on":
            args += ["--deny-tool=" + ",".join(f"docs({tool})" for tool in MCP_DENIED_TOOLS)]
    if env.get("COPILOT_PIF_MODE"):
        args += ["--additional-mcp-config", "@/scripts/copilot-pif-mcp.json"]
    args += approval
    if env.get("COPILOT_MODEL"):
        args += ["--model", env["COPILOT_MODEL"]]
    args += shlex.split(env.get("HARNESS_MECH_ARGS", ""))
    args += shlex.split(env.get("AGENT_EXTRA", ""))
    if env.get("HARNESS_APPROVAL_TRANSPORT") == "copilot-acp":
        args += ["--acp"]
    else:
        args += ["--usage-output-file", "/logs/agent/copilot-usage.json",
                 "--output-format", "json", "-p"]
    return settings, args


def main():
    if os.environ.get("PT_MODE") in ("on", "off"):
        for name in ("COPILOT_ALLOW_ALL", "GITHUB_COPILOT_PROMPT_MODE_REPO_HOOKS",
                     "GITHUB_COPILOT_PROMPT_MODE_WORKSPACE_MCP", "GITHUB_COPILOT_PROMPT_MODE_EXTENSIONS"):
            os.environ.pop(name, None)
    settings, args = configuration(os.environ)
    home = Path(os.environ["COPILOT_HOME"])
    home.mkdir(parents=True, exist_ok=True)
    (home / "settings.json").write_text(json.dumps(settings) + "\n", encoding="utf-8")
    if os.environ.get("PT_MODE"):
        profile_path = Path("/var/spool/pt/profile.json")
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["configuration_sha256"][str(home / "settings.json")] = hashlib.sha256(
            (home / "settings.json").read_bytes()).hexdigest()
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("COPILOT_MCP_MODE"):
        # Every MCP task installs this executable; StreamLoop's is an upstream
        # SQLite wrapper, while the two small tasks install the Python server.
        config = {"mcpServers": {"docs": {
            "type": "local", "command": "/usr/local/bin/mcp-server",
            "args": [], "tools": ["*"],
        }}}
        Path("/scripts/copilot-mcp.json").write_text(json.dumps(config) + "\n", encoding="utf-8")
    if args[-1] == "-p":
        args.append(Path("/scripts/instruction.md").read_text(encoding="utf-8"))
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
