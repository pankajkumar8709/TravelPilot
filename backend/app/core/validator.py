"""Phase 5 — Conflict/Validation Engine.

Standalone validator. Returns STRUCTURED violations (type, affected ids, message),
not a pass/fail flag, because Phase 7/9 need to explain WHAT is wrong.

Checks:
  - time overlaps between consecutive activities (incl. travel-time buffer)
  - activities scheduled outside opening hours
  - daily and total budget vs the user's stated limit
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable

from app.core.scheduler import PlannedActivity
from app.core.timeutil import is_open_during, to_min


@dataclass
class Violation:
    type: str  # "overlap" | "hours" | "budget_day" | "budget_total"
    activity_ids: list[int] = field(default_factory=list)
    message: str = ""


def validate_day(
    day_index: int,
    activities: list[PlannedActivity],
    travel_fn: Callable[[int, int], float],
    day_budget: float | None,
    opening_hours_fn: Callable[[int], str],
) -> list[Violation]:
    violations: list[Violation] = []
    ordered = sorted(activities, key=lambda a: a.seq)

    # time overlaps incl. travel buffer
    for prev, nxt in zip(ordered, ordered[1:]):
        travel = travel_fn(prev.place_id, nxt.place_id)
        earliest_next = to_min(prev.end_time) + travel
        if to_min(nxt.start_time) < earliest_next - 0.5:  # tolerance
            violations.append(
                Violation(
                    type="overlap",
                    activity_ids=[prev.place_id, nxt.place_id],
                    message=(
                        f"Day {day_index}: '{nxt.name}' starts {nxt.start_time} but "
                        f"'{prev.name}' ends {prev.end_time} + {travel:.0f}min travel."
                    ),
                )
            )

    # opening hours
    for a in ordered:
        oh = opening_hours_fn(a.place_id)
        if not is_open_during(oh, to_min(a.start_time), to_min(a.end_time)):
            violations.append(
                Violation(
                    type="hours",
                    activity_ids=[a.place_id],
                    message=f"Day {day_index}: '{a.name}' scheduled {a.start_time}-{a.end_time} outside opening hours ({oh}).",
                )
            )

    # daily budget
    if day_budget is not None:
        day_cost = sum(a.cost for a in ordered)
        if day_cost > day_budget + 1e-6:
            violations.append(
                Violation(
                    type="budget_day",
                    activity_ids=[a.place_id for a in ordered],
                    message=f"Day {day_index}: cost {day_cost:.2f} exceeds daily budget {day_budget:.2f}.",
                )
            )

    return violations


def validate_trip(
    days: list[tuple[int, list[PlannedActivity]]],
    travel_fn: Callable[[int, int], float],
    opening_hours_fn: Callable[[int], str],
    total_budget: float | None,
    day_budget: float | None = None,
) -> list[dict]:
    all_v: list[Violation] = []
    for idx, acts in days:
        all_v.extend(validate_day(idx, acts, travel_fn, day_budget, opening_hours_fn))

    if total_budget is not None:
        trip_cost = sum(a.cost for _, acts in days for a in acts)
        if trip_cost > total_budget + 1e-6:
            all_v.append(
                Violation(
                    type="budget_total",
                    message=f"Trip cost {trip_cost:.2f} exceeds total budget {total_budget:.2f}.",
                )
            )

    return [asdict(v) for v in all_v]
