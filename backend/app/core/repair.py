"""Phase 7 — Disruption repair (minimal-diff) + Phase 12.5 plan-stability score.

Repair pipeline (triggered identically by manual inject OR EventBridge poll):
  1. identify activities causally affected by the disruption (the affected SCOPE)
  2. re-run the Phase 4 scheduler ONLY on that scope, holding everything else fixed
  3. re-run the Phase 5 validator on the result
  4. pull 1-2 precomputed backup alternates if a direct replacement is needed
  5. package a diff (added / removed / modified + reason) for Phase 9 to render

The differentiator is that the diff is VISIBLY minimal — only the affected slice
changes. Plan-stability score = % of original activities that survive unchanged.
"""
from __future__ import annotations

from typing import Callable

from app.core.scheduler import CandidatePlace, PlannedActivity, greedy_schedule
from app.core.timeutil import to_min


def affected_scope(
    activities: list[PlannedActivity], disrupted_place_id: int
) -> tuple[list[PlannedActivity], list[PlannedActivity]]:
    """Split a day into (kept, affected). The disrupted activity and everything
    AFTER it in sequence is affected; everything before is held fixed."""
    ordered = sorted(activities, key=lambda a: a.seq)
    idx = next((i for i, a in enumerate(ordered) if a.place_id == disrupted_place_id), None)
    if idx is None:
        return ordered, []
    return ordered[:idx], ordered[idx:]


def repair_day(
    activities: list[PlannedActivity],
    disrupted_place_id: int,
    candidates: list[CandidatePlace],
    travel_fn: Callable[[int, int], float],
    window_end: int,
    day_budget: float,
    priority_tags: list[str] | None = None,
) -> tuple[list[PlannedActivity], dict]:
    """Rebuild only the affected tail. Returns (new_day, diff)."""
    kept, affected = affected_scope(activities, disrupted_place_id)

    # anchor: rebuild from the end of the last kept activity, at its location
    if kept:
        anchor = kept[-1]
        resume_time = to_min(anchor.end_time)
        start_id = anchor.place_id
        spent_before = sum(a.cost for a in kept)
    else:
        resume_time = to_min(activities[0].start_time) if activities else 9 * 60
        start_id = None
        spent_before = 0.0

    disrupted_ids = {a.place_id for a in affected}
    # candidate pool for the tail EXCLUDES the disrupted place; prefer its backups first
    tail_candidates = [c for c in candidates if c.id != disrupted_place_id and c.id not in {a.place_id for a in kept}]

    rebuilt_tail = greedy_schedule(
        candidates=tail_candidates,
        travel_fn=travel_fn,
        window=(int(resume_time), window_end),
        budget=max(0.0, day_budget - spent_before),
        start_id=start_id,
        priority_tags=priority_tags,
    )
    # renumber seq continuing after kept
    base = len(kept)
    for i, a in enumerate(rebuilt_tail):
        a.seq = base + i

    new_day = kept + rebuilt_tail

    diff = _build_diff(activities, new_day)
    return new_day, diff


def _build_diff(before: list[PlannedActivity], after: list[PlannedActivity]) -> dict:
    before_ids = {a.place_id for a in before}
    after_ids = {a.place_id for a in after}
    before_by = {a.place_id: a for a in before}
    after_by = {a.place_id: a for a in after}

    removed = [_slim(before_by[i]) for i in before_ids - after_ids]
    added = [_slim(after_by[i]) for i in after_ids - before_ids]
    modified = []
    for i in before_ids & after_ids:
        b, a = before_by[i], after_by[i]
        if (b.start_time, b.end_time, b.seq) != (a.start_time, a.end_time, a.seq):
            modified.append({"place_id": i, "name": a.name,
                             "from": f"{b.start_time}-{b.end_time}",
                             "to": f"{a.start_time}-{a.end_time}"})

    stability = plan_stability(before, after)
    return {"added": added, "removed": removed, "modified": modified, "stability": stability}


def _slim(a: PlannedActivity) -> dict:
    return {"place_id": a.place_id, "name": a.name,
            "start_time": a.start_time, "end_time": a.end_time,
            "cost": a.cost, "interest_tag": a.interest_tag}


def plan_stability(before: list[PlannedActivity], after: list[PlannedActivity]) -> float:
    """Phase 12.5 — % of original activities that survive a rebuild UNCHANGED
    (same place, same start & end time)."""
    if not before:
        return 100.0
    after_key = {(a.place_id, a.start_time, a.end_time) for a in after}
    survived = sum(1 for b in before if (b.place_id, b.start_time, b.end_time) in after_key)
    return round(100.0 * survived / len(before), 1)
