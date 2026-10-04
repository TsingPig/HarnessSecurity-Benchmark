# Harness security task suite

The suite contains 25 base tasks across 10 security mechanisms. Each task includes a specification, container environment, reference solution and independent utility verifier.

| Mechanism | Tasks | Languages | Scenarios |
|---|---:|---|---|
| [Automatic approval](aa-bench/README.md) | 2 | Python | Payment settlement; Release engineering |
| [Audit logging](al-bench/README.md) | 2 | Python | Risk scoring; Credential handling |
| [Command allowlists](cal-bench/README.md) | 2 | Python | Command-line tooling; Documentation tooling |
| [Command denylists](cdl-bench/README.md) | 2 | Python; SQL | Contact data processing; Deployment configuration |
| [Filesystem boundaries](pr-bench/README.md) | 4 | Python; C++ | Claims reconciliation; File service activation; Storage incident recovery; ML monitoring |
| [Network isolation](ni-bench/README.md) | 2 | JavaScript; Python | Dependency management; Continuous integration |
| [Read-only mode](ro-bench/README.md) | 2 | Ruby; HTML; CSS; JavaScript; Go; SQL | Takeaway ordering; Bike-share operations |
| [Prompt injection filtering](pif-bench/README.md) | 2 | Python; C# | Incident response; Terminal game integration |
| [MCP permissions](mcp-bench/README.md) | 3 | Python; JavaScript; SQL | Documentation search; Identity data validation; Creator moderation |
| [Project trust](pt-bench/README.md) | 4 | Python | SVG rendering; Sprite serialization; Audio synthesis; Mechanical simulation |

## Reproduce

Use the [execution guide](../../scripts/RQ2/README.md) to install dependencies, rebuild and validate task packages, inspect native harness modes, and run a three-attempt pilot followed by ten attempts. Each mechanism README provides its own commands.

The [Terminal-Bench task pool](terminal-bench/tasks/README.md) contains 66 task definitions with per-task language, runtime and reference-solution instructions.
