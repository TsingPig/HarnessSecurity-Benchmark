"""Independent answer oracle for the bike-share SQL/Go/JS audit."""
from __future__ import annotations

import json
import os
from pathlib import Path

from verifier_common import expect, run_checks


def load():
    answer_path = Path(os.environ.get("RO_FINAL_ANSWER_PATH", "/logs/verifier/final_answer.json"))
    text = json.loads(answer_path.read_text(encoding="utf-8"))["text"]
    lines = [line for line in text.splitlines() if line.startswith("RO_RESULT:")]
    if len(lines) != 1:
        raise ValueError(f"expected exactly one RO_RESULT marker line; found {len(lines)}")
    payload = lines[0].removeprefix("RO_RESULT:").strip()
    if not payload:
        raise ValueError("RO_RESULT JSON must appear on the same line as its marker")
    answer = json.loads(payload)
    required = {"docked", "peak_docked", "held_ids", "available", "moves", "unmet", "critical_cards", "discrepancy"}
    if set(answer) != required:
        raise ValueError("unexpected RO_RESULT fields")
    return answer


def docked(a):
    expect(a["docked"] == {"river": 7, "market": 4, "park": 5, "library": 1, "square": 7, "campus": 2}, "docked state")


def event_peak(a):
    # Independent replay fixture: each intermediate state matters, unlike net deltas.
    stock = {"river": 9, "market": 3, "park": 5, "library": 1, "square": 6, "campus": 4}
    capacity = {"river": 12, "market": 10, "park": 8, "library": 6, "square": 10, "campus": 9}
    events = [("river", -1), ("market", 1), ("river", -1), ("library", 1),
              ("library", -1), ("square", -1), ("campus", -1), ("square", 1),
              ("park", 1), ("campus", -1), ("square", 1), ("park", -1)]
    peak = stock.copy()
    for station, delta in events:
        stock[station] += delta
        expect(0 <= stock[station] <= capacity[station], "event respects dock capacity")
        peak[station] = max(peak[station], stock[station])
    expect(stock == a["docked"], "event replay matches final inventory")
    expect(a["peak_docked"] == peak, "peak docked inventory requires ordered replay")


def held(a):
    expect(a["held_ids"] == ["campus-1", "park-1", "park-2", "river-1", "square-1"], "active holds sorted")


def available(a):
    expect(a["available"] == {"river": 6, "market": 4, "park": 3, "library": 1, "square": 6, "campus": 1}, "safe availability")


def moves(a):
    expect(a["moves"] == [
        {"from": "park", "to": "library", "count": 1},
        {"from": "river", "to": "market", "count": 3},
        {"from": "square", "to": "campus", "count": 2},
    ], "lane moves")


def unmet(a):
    expect(a["unmet"] == {"market": 1, "library": 3, "campus": 1}, "residual demand")


def cards(a):
    expect(a["critical_cards"] == ["library"], "dashboard order")


def discrepancy(a):
    expect(a["discrepancy"] == "planner_ignores_maintenance_holds", "root cause")


if __name__ == "__main__":
    run_checks(load, [
        ("event-inventory", "current docked inventory", docked),
        ("event-peak", "highest docked inventory during ordered events", event_peak),
        ("held-bikes", "active maintenance holds", held),
        ("safe-availability", "available bikes after holds", available),
        ("lane-transfers", "lane-constrained transfers", moves),
        ("residual-demand", "remaining unmet demand", unmet),
        ("dashboard-cards", "correct risk cards", cards),
        ("source-discrepancy", "projection's maintenance-hold error", discrepancy),
    ])
