"""Phase 4 — time-anchored food & stay suggestions (the scheduler's second pass).

Does NOT add anything to the itinerary; it attaches suggestions to moments in it.
  - meal windows: midday gap (lunch) + after last activity ~7-10pm (dinner),
    dinner computed from when the last activity ACTUALLY ends, not a fixed clock.
  - food: rank cached food places by travel time from the pre-gap location,
    filtered to likely-open-in-window.
  - stay: rank cached hotels by proximity to BOTH today's last activity and
    tomorrow's first planned activity (avoid a bad next-day commute).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.core.scheduler import CandidatePlace, PlannedActivity
from app.core.timeutil import is_open_during, to_min


@dataclass
class MealWindow:
    type: str          # "lunch" | "dinner"
    label: str         # "lunch ~12-2pm"
    from_lat: float
    from_lon: float
    from_place_id: int
    win_start: int     # minutes
    win_end: int


def detect_meal_windows(activities: list[PlannedActivity]) -> list[MealWindow]:
    if not activities:
        return []
    ordered = sorted(activities, key=lambda a: a.seq)
    windows: list[MealWindow] = []

    # lunch: a gap overlapping ~11:30-14:30 with no activity
    LUNCH_LO, LUNCH_HI = to_min("11:30"), to_min("14:30")
    for prev, nxt in zip(ordered, ordered[1:]):
        gap_start, gap_end = to_min(prev.end_time), to_min(nxt.start_time)
        if gap_end - gap_start >= 45 and gap_start < LUNCH_HI and gap_end > LUNCH_LO:
            windows.append(
                MealWindow("lunch", "lunch ~12-2pm", prev.lat, prev.lon, prev.place_id,
                           max(gap_start, LUNCH_LO), min(gap_end, LUNCH_HI))
            )
            break

    # dinner: after the last activity ends (computed from real end time)
    last = ordered[-1]
    d_start = to_min(last.end_time)
    d_end = min(d_start + 150, to_min("22:30"))
    if d_end - d_start >= 30:
        windows.append(
            MealWindow("dinner", f"dinner ~{last.end_time}-{_fmt(d_end)}",
                       last.lat, last.lon, last.place_id, d_start, d_end)
        )
    return windows


def _fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _dist(a_lat, a_lon, b_lat, b_lon) -> float:
    # cheap planar proxy — fine for ranking within one city
    return ((a_lat - b_lat) ** 2 + (a_lon - b_lon) ** 2) ** 0.5


def rank_food(
    window: MealWindow,
    food_places: list[CandidatePlace],
    top_n: int = 3,
) -> list[tuple[CandidatePlace, int]]:
    """Top-N food places near the window's location, likely open in-window."""
    open_ones = [
        p for p in food_places
        if is_open_during(p.opening_hours, window.win_start, min(window.win_start + 60, window.win_end))
    ]
    open_ones.sort(key=lambda p: _dist(window.from_lat, window.from_lon, p.lat, p.lon))
    return [(p, i + 1) for i, p in enumerate(open_ones[:top_n])]


def rank_stay(
    last_activity: PlannedActivity,
    tomorrow_first: PlannedActivity | None,
    hotels: list[CandidatePlace],
    top_n: int = 3,
) -> list[tuple[CandidatePlace, int]]:
    """Rank hotels on combined proximity to today's end AND tomorrow's first stop."""
    def score(h: CandidatePlace) -> float:
        s = _dist(last_activity.lat, last_activity.lon, h.lat, h.lon)
        if tomorrow_first is not None:
            s += _dist(tomorrow_first.lat, tomorrow_first.lon, h.lat, h.lon)
        return s

    ranked = sorted(hotels, key=score)
    return [(h, i + 1) for i, h in enumerate(ranked[:top_n])]
