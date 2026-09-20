"""Unit tests for the plan's deterministic core (Phases 4, 5, 7, 12.5).

Run:  cd backend && python -m pytest -v
"""
from __future__ import annotations

from app.core.scheduler import CandidatePlace, PlannedActivity, greedy_schedule
from app.core.validator import validate_trip
from app.core.suggestions import detect_meal_windows
from app.core.repair import affected_scope, repair_day, plan_stability


# --- a tiny synthetic dataset: 5 places on a line, 15 min apart pairwise ---
PLACES = [
    CandidatePlace(1, "Museum", 0.0, 0.0, "culture", "culture", "09:00-18:00", 90, 20.0),
    CandidatePlace(2, "Park", 0.0, 0.1, "outdoor", "outdoor", "", 60, 0.0),
    CandidatePlace(3, "Gallery", 0.0, 0.2, "culture", "culture", "10:00-17:00", 60, 15.0),
    CandidatePlace(4, "Market", 0.0, 0.3, "food", "food", "08:00-20:00", 45, 10.0),
    CandidatePlace(5, "Tower", 0.0, 0.4, "outdoor", "outdoor", "09:00-22:00", 60, 25.0),
]
BY_ID = {p.id: p for p in PLACES}


def travel_fn(a, b):
    if a is None or b is None:
        return 0.0
    return 15.0  # flat 15 min for the test


def oh_fn(pid):
    return BY_ID[pid].opening_hours


def test_scheduler_produces_ordered_nonoverlapping_day():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=100.0, start_id=None)
    assert len(plan) >= 3
    # seq is monotonic and times are non-decreasing
    for prev, nxt in zip(plan, plan[1:]):
        assert nxt.seq == prev.seq + 1
        assert nxt.start_time >= prev.end_time


def test_scheduler_respects_budget():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=25.0, start_id=None)
    assert sum(a.cost for a in plan) <= 25.0


def test_scheduler_honours_priority_tags():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=100.0,
                           start_id=None, priority_tags=["food"])
    assert plan[0].interest_tag == "food"  # food prioritized first


def test_validator_flags_overbudget():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=1000.0, start_id=None)
    v = validate_trip([(1, plan)], travel_fn, oh_fn, total_budget=5.0, day_budget=5.0)
    types = {x["type"] for x in v}
    assert "budget_day" in types or "budget_total" in types


def test_validator_flags_deliberate_overlap():
    # Phase 5 exit criterion: a deliberately broken itinerary returns structured violations.
    # Two activities 15min apart in travel, but scheduled back-to-back with no buffer.
    from app.core.scheduler import PlannedActivity
    broken = [
        PlannedActivity(1, "A", "09:00", "10:00", 60, 0.0, "culture", 0, 0.0, 0.0),
        PlannedActivity(3, "B", "10:00", "11:00", 60, 0.0, "culture", 1, 0.0, 0.2),  # ignores 15min travel
    ]
    v = validate_trip([(1, broken)], travel_fn, oh_fn, total_budget=None)
    overlaps = [x for x in v if x["type"] == "overlap"]
    assert overlaps, "should flag the missing travel buffer as an overlap"
    assert overlaps[0]["activity_ids"] == [1, 3]
    assert "travel" in overlaps[0]["message"].lower()


def test_validator_flags_out_of_hours():
    from app.core.scheduler import PlannedActivity
    # Museum (id=1) opens 09:00-18:00; schedule it at 19:00-20:00 -> out of hours.
    broken = [PlannedActivity(1, "Museum", "19:00", "20:00", 60, 0.0, "culture", 0, 0.0, 0.0)]
    v = validate_trip([(1, broken)], travel_fn, oh_fn, total_budget=None)
    assert any(x["type"] == "hours" for x in v)


def test_validator_clean_plan_has_no_violations():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=1000.0, start_id=None)
    v = validate_trip([(1, plan)], travel_fn, oh_fn, total_budget=1000.0, day_budget=1000.0)
    assert v == []


def test_meal_windows_detects_dinner_after_last_activity():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=1000.0, start_id=None)
    windows = detect_meal_windows(plan)
    assert any(w.type == "dinner" for w in windows)


def test_affected_scope_holds_prefix_fixed():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=1000.0, start_id=None)
    disrupted = plan[1].place_id
    kept, affected = affected_scope(plan, disrupted)
    assert all(a.seq < plan[1].seq for a in kept)
    assert affected[0].place_id == disrupted


def test_repair_is_minimal_and_reports_stability():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=1000.0, start_id=None)
    disrupted = plan[-1].place_id  # disrupt the LAST activity -> minimal change
    new_day, diff = repair_day(plan, disrupted, PLACES, travel_fn,
                               window_end=21 * 60, day_budget=1000.0)
    # disrupted place must be gone from the rebuilt day
    assert disrupted not in {a.place_id for a in new_day}
    # stability is a percentage and the prefix survived
    assert 0.0 <= diff["stability"] <= 100.0
    assert diff["removed"], "the disrupted activity should appear as removed"


def test_plan_stability_full_when_identical():
    plan = greedy_schedule(PLACES, travel_fn, (9 * 60, 21 * 60), budget=1000.0, start_id=None)
    assert plan_stability(plan, plan) == 100.0
