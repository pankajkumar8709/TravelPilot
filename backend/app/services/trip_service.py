"""Trip service — orchestrates Phase 4 generation over cached data.

- loads candidates + travel times from the DB (Phase 3 cache, no runtime API calls)
- asks Bedrock for category priorities / budget split (Phase 4; mock-safe)
- runs the greedy scheduler per day, persists activities
- precomputes 1-2 backup alternates per activity (Phase 7 requirement)
- attaches time-anchored food + stay suggestions (Phase 4 second pass)
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.scheduler import CandidatePlace, PlannedActivity, greedy_schedule
from app.core.suggestions import detect_meal_windows, rank_food, rank_stay
from app.core.timeutil import to_min
from app.models import Activity, Day, Place, Suggestion, TravelTime, Trip
from app.services import llm

SCHEDULABLE = {"culture", "outdoor", "history", "shopping", "nightlife"}


def _travel_map(db: Session) -> dict[tuple[int, int], float]:
    return {(t.from_id, t.to_id): t.duration_minutes for t in db.query(TravelTime).all()}


def _candidates(db: Session) -> list[CandidatePlace]:
    out = []
    for p in db.query(Place).all():
        out.append(CandidatePlace(
            id=p.id, name=p.name, lat=p.lat, lon=p.lon, category=p.category,
            interest_tag=p.interest_tag, opening_hours=p.opening_hours,
            avg_visit_minutes=p.avg_visit_minutes, cost=p.cost, website=p.website,
            image_url=p.image_url,
        ))
    return out


def generate_trip(db: Session, trip: Trip) -> Trip:
    all_places = _candidates(db)
    tmap = _travel_map(db)

    def travel_fn(a, b):
        if a is None or b is None:
            return 0.0
        return tmap.get((a, b), tmap.get((b, a), 20.0))

    n_days = max(1, (date.fromisoformat(trip.end_date) - date.fromisoformat(trip.start_date)).days + 1)
    pri = llm.prioritize_interests(" ".join(trip.interests), trip.budget_total, n_days)
    priority_tags = pri["priority_tags"]
    day_budget = pri.get("daily_budget") or (trip.budget_total / n_days if trip.budget_total else 1e9)

    schedulable = [c for c in all_places if c.category in SCHEDULABLE]
    food = [c for c in all_places if c.category == "food"]
    hotels = [c for c in all_places if c.category == "hotel"]
    hotel_id = trip.hotel_place_id or (hotels[0].id if hotels else None)

    # wipe any prior days for idempotent regeneration
    for d in list(trip.days):
        db.delete(d)
    db.flush()

    used_across_trip: set[int] = set()
    day_plans: list[tuple[Day, list[PlannedActivity]]] = []

    # pace controls how late the day runs (packed = longer, relaxed = shorter)
    day_end = {"relaxed": "18:00", "balanced": "21:00", "packed": "22:30"}.get(trip.pace, "21:00")

    for i in range(n_days):
        d_date = (date.fromisoformat(trip.start_date) + timedelta(days=i)).isoformat()
        # day 1 begins at the journey start time; later days at a normal morning start
        day_start = trip.start_time_day1 if i == 0 else "09:00"
        day = Day(trip_id=trip.id, date=d_date, day_index=i + 1,
                  start_time=day_start, end_time=day_end)
        db.add(day)
        db.flush()

        pool = [c for c in schedulable if c.id not in used_across_trip]
        plan = greedy_schedule(
            candidates=pool, travel_fn=travel_fn,
            window=(to_min(day_start), to_min(day_end)),
            budget=day_budget, start_id=hotel_id, priority_tags=priority_tags,
        )
        for a in plan:
            used_across_trip.add(a.place_id)
            # Phase 7: precompute 1-2 backups — same tag, not already used
            backups = [c.id for c in schedulable
                       if c.interest_tag == a.interest_tag and c.id != a.place_id
                       and c.id not in used_across_trip][:2]
            a.backups = backups
            db.add(Activity(
                day_id=day.id, place_id=a.place_id, name=a.name,
                start_time=a.start_time, end_time=a.end_time,
                duration_minutes=a.duration_minutes, cost=a.cost,
                interest_tag=a.interest_tag, seq=a.seq, lat=a.lat, lon=a.lon,
                backups=backups, image_url=a.image_url,
            ))
        day_plans.append((day, plan))

    # Phase 4 second pass: suggestions (needs tomorrow's first activity for stays)
    for idx, (day, plan) in enumerate(day_plans):
        if not plan:
            continue
        for w in detect_meal_windows(plan):
            for p, rank in rank_food(w, food, top_n=3):
                db.add(Suggestion(day_id=day.id, type="food", time_window=w.label,
                                  place_id=p.id, place_name=p.name, rank=rank,
                                  lat=p.lat, lon=p.lon, website=p.website))
        tomorrow_first = day_plans[idx + 1][1][0] if idx + 1 < len(day_plans) and day_plans[idx + 1][1] else None
        for h, rank in rank_stay(plan[-1], tomorrow_first, hotels, top_n=3):
            db.add(Suggestion(day_id=day.id, type="stay", time_window="tonight",
                              place_id=h.id, place_name=h.name, rank=rank,
                              lat=h.lat, lon=h.lon, website=h.website))

    db.commit()
    db.refresh(trip)
    return trip
