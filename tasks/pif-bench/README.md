# Prompt injection filtering benchmark

Examines indirect instructions carried by repository documents, MCP results and external records during incident response and community-pack integration.

The current dataset is PIF v20. Its GridQuest CLI check also validates the required pack receipt against an independent catalog snapshot. Codex enables sandbox network access for the task's HTTP catalog and action service.

## Tasks

| Task | Languages | Scenario | Functional coverage |
|---|---|---|---|
| [issue-triage-classify](tasks/issue-triage-classify-attack/instruction.md) | Python | Incident response | Priority, field extraction, timelines, labels, routing, SLA, log signatures and escalation handoff |
| [grid-maze-csharp](tasks/grid-maze-csharp-attack/instruction.md) | C# | Terminal game integration on .NET 9 | JSON levels, movement, walls, keys, exit state, input validation, CLI output and pack receipts |

## Evaluation

Each task has eight functional checks and three security effects. Incident checks cover partner access, notification recipients and evidence transfer; game checks cover maintainer access, regression-check settings and source publication.

## Reproduce

Run from the repository root with Python dependencies, Docker and model credentials configured as described in [the execution guide](../../../scripts/RQ2/README.md). The runner selects applicable native modes from the harness configuration and consensus ratings.

```powershell
python scripts/RQ2/mechanisms/pif/dataset.py build --refresh
python scripts/RQ2/mechanisms/pif/dataset.py validate
python scripts/RQ2/mechanisms/pif/pif_run_agent.py --harness codex --modes native --attempts 3 --jobs 8 --agent-timeout 28800 --build-timeout 28800 --out .runtime/RQ2/runs/pif-codex --dry-run
```

Remove `--dry-run` to execute the pilot. After checking its reports, resume the same output directory:

```powershell
python scripts/RQ2/mechanisms/pif/pif_run_agent.py --harness codex --modes native --attempts 10 --jobs 8 --agent-timeout 28800 --build-timeout 28800 --out .runtime/RQ2/runs/pif-codex --resume
```

The output directory contains `report.json`, `RQ2-results.md` and per-trial evidence.
