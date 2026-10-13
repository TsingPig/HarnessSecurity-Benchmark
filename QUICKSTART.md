# HarnessSecurity-Bench Quickstart

[中文](QUICKSTART.zh-CN.md)

Run commands from the repository root. After setup and credentials, go to **Run an experiment**; validation is optional.

## Set up Python and Docker

- Python 3.11+ (tested: 3.13). Host scripts use the standard library.
- Docker with Linux containers and user namespace support for native sandboxes. Gemini/Qwen NI also needs nested Docker.
- Internet access and a model API key.

Check `python --version` and `docker info`.

## Configure model credentials

Set variables in the shell that launches the runner:

```powershell
$env:AGENT_API_KEY = '<your-api-key>'
$env:AGENT_BASE_URL = 'https://<your-provider>/v1'
$env:AGENT_MODEL = '<model-id>'
```

In Bash, use `export NAME='value'`. For other harnesses, use the configuration below:

| Harness ID | Credentials and API protocol |
|---|---|
| `codex` | `AGENT_*`; Responses API. |
| `copilot-agent`, `gptme`, `qwen` | `AGENT_*`; OpenAI-compatible provider. |
| `claude-code` | `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`, `AGENT_MODEL`; optional `ANTHROPIC_BASE_URL` for Anthropic Messages. |
| `gemini-cli` | `GEMINI_API_KEY` or `GOOGLE_API_KEY`, `GEMINI_CLI_MODEL`; optional `GOOGLE_GEMINI_BASE_URL` for Gemini API. |

For AA OFF, set `REVIEWER_MODEL` to a different model. External reviewers use `REVIEWER_BASE_URL`/`REVIEWER_API_KEY` (default: `AGENT_BASE_URL`/`AGENT_API_KEY`) and require chat completions. Codex uses the acting endpoint and credentials for both models.

**Optional: validate tasks and preview the run**

These commands check the package or execution plan without building images or calling models.

Validate task files:

```text
python scripts/cal/cal_run_agent.py --validate
```

Preview the selected tasks and modes:

```text
python scripts/cal/cal_run_agent.py --harness codex --attempts 3 --jobs 3 --agent-timeout 28800 --out .runtime/runs/cal-codex --dry-run
```

## Run an experiment

This command builds Docker images and calls the model:

```text
python scripts/cal/cal_run_agent.py --harness codex --attempts 3 --jobs 3 --agent-timeout 28800 --out .runtime/runs/cal-codex
```

The CAL/Codex pilot runs three attempts per task and applicable mode, with three parallel jobs and an eight-hour deadline per trial.

Replace `codex` with a harness ID above. Other mechanisms use `scripts/<id>/<id>_run_agent.py`:

| ID | Mechanism |
|---|---|
| `aa` | Automatic approval |
| `cal` | Command allowlists |
| `cdl` | Command denylists |
| `mcp` | MCP permissions |
| `ni` | Network isolation |
| `pif` | Prompt injection filtering |
| `pr` | Filesystem boundaries |
| `pt` | Project trust |
| `ro` | Read-only mode |

Use a new output directory per configuration. Select tasks with `--tasks <task-id> ...` and modes with `--modes <mode> ...`; see `--help` for options.

Codex/Qwen PIF uses `--modes native`. Gemini/Qwen NI needs an HTTPS model endpoint reachable from the Docker host.

## Resume to ten attempts

After a healthy pilot, continue the same run with five parallel jobs:

```text
python scripts/cal/cal_run_agent.py --harness codex --attempts 10 --jobs 5 --agent-timeout 28800 --out .runtime/runs/cal-codex --resume
```

Ten is the total target. Keep the output directory and experiment configuration; include `--modes native` again for Codex/Qwen PIF.

## View results

Open the files in the output directory:

- `results.md`: result tables.
- `report.json`: trial outcomes, metrics, and token usage.
