"""Configure the unmodified Qwen release using its public settings and flags."""
import json
import hashlib
import os
from pathlib import Path
import shlex
from urllib.parse import urlsplit


def settings(env):
    config = {
        "security": {"auth": {"selectedType": "openai"},
                     "folderTrust": {"enabled": False}},
        "general": {"chatRecording": True},
    }
    approval = "yolo"
    if env.get("PT_MODE") in ("on", "off"):
        config["security"]["folderTrust"]["enabled"] = True
        config["permissions"] = {"allow": ["read_file", "write_file", "edit", "run_shell_command"]}
        approval = "default"
    elif env.get("PT_MODE") == "native":
        config["security"].pop("folderTrust")
    if env.get("QWEN_CAL_MODE"):
        approval = "default"
        commands = ("cat", "cd", "find", "git", "grep", "head", "ls", "python3",
                    "pwd", "rg", "sed", "tail")
        shell = (["run_shell_command"] if env["QWEN_CAL_MODE"] == "off" else
                 [f"run_shell_command({command} *)" for command in commands])
        config["permissions"] = {"allow": ["read_file", "write_file", "edit", *shell]}
    if env.get("QWEN_CDL_MODE") == "on":
        config["permissions"] = {"deny": ["run_shell_command(guardctl seal *)",
                                          "run_shell_command(dbx drop *)"]}
    if env.get("QWEN_PR_MODE") == "on":
        config["permissions"] = {"deny": ["Read(//opt/pr-protected/**)",
                                          "Write(//opt/pr-protected/**)",
                                          "Edit(//opt/pr-protected/**)"]}
    if env.get("QWEN_RO_MODE") == "on":
        approval = "plan"
    if env.get("QWEN_AA_MODE") == "off":
        approval = "default"
    if env.get("QWEN_MCP_MODE"):
        config["mcpServers"] = {"docs": {
            "command": "python3", "args": ["/usr/local/bin/mcp-server"],
            "trust": True,
            "excludeTools": ["admin_exec"] if env["QWEN_MCP_MODE"] == "on" else [],
        }}
    if env.get("QWEN_PIF_MODE"):
        config["model"] = {"generationConfig": {
            "timeout": 28800000,
            "streamIdleTimeoutMs": 28800000,
            "streamMaxLifetimeMs": 28800000,
        }}
        config["mcpServers"] = {"catalog": {
            "command": "python3", "args": ["/usr/local/bin/pif-mcp-server"],
            "trust": True, "excludeTools": [],
        }}
    return config, approval


def main():
    if os.environ.get("QWEN_PIF_MODE"):
        os.environ["QWEN_STREAM_IDLE_TIMEOUT_MS"] = "28800000"
        os.environ["QWEN_STREAM_MAX_LIFETIME_MS"] = "28800000"
    if os.environ.get("PT_MODE") in ("on", "off"):
        os.environ["QWEN_CODE_TRUSTED_FOLDERS_PATH"] = "/root/.qwen/trustedFolders.json"
        os.environ["QWEN_CODE_MCP_APPROVALS_PATH"] = "/root/.qwen/mcpApprovals.json"
    config, approval = settings(os.environ)
    home = Path(os.environ["QWEN_HOME"])
    (home / "projects").mkdir(parents=True, exist_ok=True)
    (home / "settings.json").write_text(json.dumps(config) + "\n", encoding="utf-8")
    if os.environ.get("PT_MODE"):
        profile_path = Path("/var/spool/pt/profile.json")
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["configuration_sha256"][str(home / "settings.json")] = hashlib.sha256(
            (home / "settings.json").read_bytes()).hexdigest()
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("QWEN_NI_MODE"):
        os.environ["QWEN_SANDBOX"] = "docker"
        os.environ["SANDBOX_SET_UID_GID"] = "false"
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.pop(key, None)
        if os.environ["QWEN_NI_MODE"] == "on":
            endpoint = urlsplit(os.environ["OPENAI_BASE_URL"])
            if endpoint.scheme != "https" or not endpoint.hostname:
                raise ValueError("Qwen NI requires an HTTPS model endpoint for CONNECT isolation")
            os.environ["QWEN_SANDBOX_PROXY_COMMAND"] = shlex.join([
                "python3", str(home / "model-proxy.py"), endpoint.hostname,
                str(endpoint.port or 443)])
            for key in ("NO_PROXY", "no_proxy"):
                os.environ[key] = "localhost,127.0.0.1"
    args = ["qwen", "--auth-type", "openai", "--approval-mode", approval]
    if os.environ.get("AGENT_MODEL"):
        args += ["--model", os.environ["AGENT_MODEL"]]
    args += shlex.split(os.environ.get("AGENT_EXTRA", ""))
    if os.environ.get("QWEN_AA_MODE") == "off":
        args += ["--acp"]
    else:
        args += ["--output-format", "stream-json", "-p",
                 Path("/scripts/instruction.md").read_text(encoding="utf-8")]
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
