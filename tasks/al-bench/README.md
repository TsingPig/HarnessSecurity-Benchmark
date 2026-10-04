# Audit logging benchmark

Measures coverage of sensitive operations in the harness native audit output, using independently recorded action identifiers.

## Tasks

| Task | Languages | Scenario | Functional coverage |
|---|---|---|---|
| [risk-score-weights](tasks/risk-score-weights-attack/instruction.md) | Python | Risk scoring | Weighted event scores, cumulative replay and weight calibration |
| [redact-secrets](tasks/redact-secrets-attack/instruction.md) | Python | Credential handling | Secret-key detection, non-mutating masking and redaction reports |

## Evaluation

The task carriers introduce credential-rotation operations. Security checks compare performed action IDs with host-captured native tool-call and result evidence. Functional checks run in an independent verifier image.

## Reproduce

Run from the repository root with Python dependencies, Docker and model credentials configured as described in [the execution guide](../../../scripts/RQ2/README.md). The runner selects applicable native modes from the harness configuration and consensus ratings.

```powershell
python scripts/RQ2/mechanisms/al/dataset.py build --refresh
python scripts/RQ2/mechanisms/al/dataset.py validate
python scripts/RQ2/mechanisms/al/al_run_agent.py --harness codex --attempts 3 --jobs 3 --agent-timeout 28800 --out .runtime/RQ2/runs/al-codex --dry-run
```

Remove `--dry-run` to execute the pilot. After checking its reports, resume the same output directory:

```powershell
python scripts/RQ2/mechanisms/al/al_run_agent.py --harness codex --attempts 10 --jobs 5 --agent-timeout 28800 --out .runtime/RQ2/runs/al-codex --resume
```

The output directory contains `report.json`, `RQ2-results.md` and per-trial evidence.
