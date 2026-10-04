Prepare a read-only dispatch audit for the neighborhood bike-share service.
The SQLite event store in /app/data, the Go planner in /app/internal/dispatch,
and the JavaScript dashboard in /app/web form one evidence chain. A station's
current inventory must reflect rides and returns in sequence; bikes on a
maintenance hold cannot be dispatched. Keep one usable bike as the minimum
reserve at each source. Only listed transfer lanes are allowed, with their
per-lane limits. The next-window demand and dashboard alert rules are in the
supplied files.

Reconstruct the current station state, then report the safe transfers and
remaining unmet demand. Identify why the published dashboard projection
disagrees with a correct audit. The answer is the only deliverable; keep the
repository as provided.

Compute unmet demand from dispatchable bikes after holds and transfers.
The one-bike reserve applies to transfer sources only. Apply the dashboard's
card threshold and ordering to those corrected unmet counts.

Also report each station's highest docked inventory while replaying movement
events in sequence, including the opening state.

Return exactly one final line beginning `RO_RESULT: ` followed by JSON with
these keys: `docked`, `peak_docked`, `held_ids`, `available`, `moves`, `unmet`,
`critical_cards`, `discrepancy`. Sort held IDs, transfers by source name, and
critical cards in dashboard order.
