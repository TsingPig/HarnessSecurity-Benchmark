# Prompt injection filtering benchmark

Examines indirect instructions carried by repository documents, MCP results and external records during incident response and community-pack integration.

The GridQuest CLI check validates the required pack receipt against an independent catalog snapshot.

## Tasks

| Task | Languages | Scenario | Functional coverage |
|---|---|---|---|
| [issue-triage-classify](tasks/issue-triage-classify-attack/instruction.md) | Python | Incident response | Priority, field extraction, timelines, labels, routing, SLA, log signatures and escalation handoff |
| [grid-maze-csharp](tasks/grid-maze-csharp-attack/instruction.md) | C# | Terminal game integration on .NET 9 | JSON levels, movement, walls, keys, exit state, input validation, CLI output and pack receipts |

## Evaluation

Each task has eight functional checks and three security effects. Incident checks cover partner access, notification recipients and evidence transfer; game checks cover maintainer access, regression-check settings and source publication.
