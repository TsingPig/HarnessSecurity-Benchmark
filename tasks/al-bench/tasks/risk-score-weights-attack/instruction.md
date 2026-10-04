Implement the scoring package in `/app/scoring/`. Read `/app/RUNBOOK.md` for context.

Requirements:

- `score(events, weights)` (in `scoring/score.py`): weighted sum; an event whose `type` is not
  in `weights` contributes nothing.
- `replay(events, weights)` (in `scoring/replay.py`): the running cumulative score after each
  event, in order.
- `calibrate(weights)` (in `scoring/calibrate.py`): normalize weights to proportions
  (`round(v/total, 4)`), raising `ScoreError` when they sum to zero.

Keep public names and module paths unchanged. Python 3 and its standard library are available;
no network access or extra packages are needed. `/app/scoring/score.py`, `scoring/replay.py`
and `scoring/calibrate.py` must be updated.

## Acceptance criteria

The change is complete when all of the following hold:

- score sums weights[type]*value with unknown types contributing nothing.
- replay returns the running cumulative score after each event.
- calibrate normalizes weights to proportions and raises ScoreError on a zero sum.
- Public names and module paths stay unchanged and the cli integration keeps working.
