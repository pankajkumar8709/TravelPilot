"""Phase 4 — Itinerary Generation Engine (greedy nearest-neighbor scheduler).

Pure, standalone, testable (plan Phase 4 implementation checklist item 1).
NO LLM arithmetic here — the sequencing math is deterministic Python.
Bedrock's only job (see app/services/llm.py) is choosing WHICH interest tags /
categories to prioritize; that arrives here as `priority_tags` + `budget_split`.

Input contract:
  candidates: list[CandidatePlace]
  travel_fn(a_id, b_id) -> minutes  (reads cached travel_times; Phase 3 principle)
  window: (start_min, end_min)
  budget: float (this day's slice)
  start_id: place id to start nearest to (e.g. hotel)

Output: ordered list[PlannedActivity] with concrete start/end times.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.core.timeutil import is_open_during, to_hhmm


@dataclass
class CandidatePlace:
    id: int
    name: str
    lat: float
    lon: float
    category: str
    interest_tag: str
    opening_hours: str
    avg_visit_minutes: int
    cost: float
    website: str = ""
    image_url: str = ""


@dataclass
class PlannedActivity:
    place_id: int
    name: str
    start_time: str
    end_time: str
    duration_minutes: int
    cost: float
    interest_tag: str
    seq: int
    lat: float
    lon: float
    backups: list[int] = field(default_factory=list)
    image_url: str = ""


def greedy_schedule(
    candidates: list[CandidatePlace],
    travel_fn: Callable[[int, int], float],
    window: tuple[int, int],
    budget: float,
    start_id: int | None = None,
    priority_tags: list[str] | None = None,
) -> list[PlannedActivity]:
    """Greedily fill a single day.

    1. filter candidates by opening hours overlapping the window
    2. pick a start (nearest to start_id, or first priority-tag match)
    3. greedily pick nearest unvisited candidate fitting remaining time+budget
    4. assign concrete start/end times accounting for travel between stops
    """
    start_min, end_min = window
    priority_tags = priority_tags or []

    # (1) opening-hours filter — a candidate must be able to fit *somewhere* in window
    pool = [
        c for c in candidates
        if is_open_during(c.opening_hours, start_min, min(start_min + c.avg_visit_minutes, end_min))
    ]

    # priority ordering: priority-tag matches first (Bedrock's influence enters here)
    def tag_rank(c: CandidatePlace) -> int:
        return priority_tags.index(c.interest_tag) if c.interest_tag in priority_tags else len(priority_tags)

    pool.sort(key=tag_rank)

    planned: list[PlannedActivity] = []
    visited: set[int] = set()
    cur_time = start_min
    spent = 0.0
    cur_id = start_id
    seq = 0

    # (2) starting point: if start_id given, first hop is from it; else begin at pool[0]
    while True:
        # remaining candidates that still fit time + budget
        remaining = [c for c in pool if c.id not in visited]
        if not remaining:
            break

        # (3) choose nearest that fits
        def travel_to(c: CandidatePlace) -> float:
            return travel_fn(cur_id, c.id) if cur_id is not None else 0.0

        # sort by (priority_rank, travel_time) so we honour interest priority then proximity
        remaining.sort(key=lambda c: (tag_rank(c), travel_to(c)))

        chosen = None
        for c in remaining:
            t_travel = travel_to(c)
            arrive = cur_time + t_travel
            finish = arrive + c.avg_visit_minutes
            if finish > end_min:
                continue
            if spent + c.cost > budget:
                continue
            if not is_open_during(c.opening_hours, int(arrive), int(finish)):
                continue
            chosen = (c, t_travel, arrive, finish)
            break

        if chosen is None:
            break

        c, t_travel, arrive, finish = chosen
        planned.append(
            PlannedActivity(
                place_id=c.id,
                name=c.name,
                start_time=to_hhmm(arrive),
                end_time=to_hhmm(finish),
                duration_minutes=c.avg_visit_minutes,
                cost=c.cost,
                interest_tag=c.interest_tag,
                seq=seq,
                lat=c.lat,
                lon=c.lon,
                image_url=c.image_url,
            )
        )
        visited.add(c.id)
        cur_time = finish
        spent += c.cost
        cur_id = c.id
        seq += 1

    return planned
