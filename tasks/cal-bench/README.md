# Command allowlists benchmark

Examines command execution under the harness native allowlist while an agent repairs a package and produces a required validation artifact.

## Tasks

| Task | Languages | Scenario | Functional coverage |
|---|---|---|---|
| [cli-arg-parser](tasks/cli-arg-parser-attack/instruction.md) | Python | Command-line tooling | Option parsing, schema coercion, error handling and parser validation reports |
| [md-table-render](tasks/md-table-render-attack/instruction.md) | Python | Documentation tooling | Cell escaping, column widths, alignment and rendered preview output |

## Evaluation

Low-trust runner records and release guidance introduce the argcheck and reportctl helpers. Security checks use invocation events; utility checks validate package behavior and required reports.

## Reproduce

Run from the repository root with Python dependencies, Docker and model credentials configured as described in [the execution guide](../../../scripts/RQ2/README.md). The runner selects applicable native modes from the harness configuration and consensus ratings.

```powershell
python scripts/RQ2/mechanisms/cal/dataset.py build --refresh
python scripts/RQ2/mechanisms/cal/dataset.py validate
python scripts/RQ2/mechanisms/cal/cal_run_agent.py --harness codex --attempts 3 --jobs 3 --agent-timeout 28800 --out .runtime/RQ2/runs/cal-codex --dry-run
```

Remove `--dry-run` to execute the pilot. After checking its reports, resume the same output directory:

```powershell
python scripts/RQ2/mechanisms/cal/cal_run_agent.py --harness codex --attempts 10 --jobs 5 --agent-timeout 28800 --out .runtime/RQ2/runs/cal-codex --resume
```

The output directory contains `report.json`, `RQ2-results.md` and per-trial evidence.
