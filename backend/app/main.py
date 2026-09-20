"""FastAPI app — TravelPilot API.

Routes:
  GET  /health
  GET  /places                         reference data (map/setup)
  GET  /amenities                       Phase 9 overlay
  POST /trips                           create + generate (Phase 2/4)
  GET  /trips/{id}                      full itinerary + suggestions (Phase 2/4)
  GET  /trips/{id}/budget               Phase 6 rollup (+ currency)
  POST /disruptions/inject             Phase 7 — manual OR synthetic-event entry (identical path)
  POST /trips/{id}/changes/{cid}/confirm   Phase 7/12.1 — apply pending change
  POST /trips/{id}/changes/{cid}/reject
  POST /nl/query                        Phase 8 — NL interface (no DB access by the model)
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.core.scheduler import PlannedActivity
from app.core.repair import repair_day
from app.core.timeutil import to_min
from app.db import get_db, init_db
from app.models import Activity, Booking, Day, ItineraryChange, Place, Trip, Amenity, Suggestion, TravelTime, Route
from app.schemas import (ChatAdd, ChatChangeDestination, ChatExplore, ChatMessage,
                         ChatMove, ChatReorder, ChatNearby, CityPrep, DisruptionInject,
                         NLQuery, TripCreate)
from app.services import llm
from app.services.trip_service import generate_trip
from app.services import ors as ors_service
from app.services import city as city_service

app = FastAPI(title="TravelPilot", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins != "*" else ["*"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    # Deploy convenience: on a FRESH database, auto-seed reference data + one demo
    # trip so the deployed app renders immediately (Phase 2's live-URL criterion).
    # Controlled by AUTO_SEED (default on); safe/idempotent — only seeds if empty.
    if settings.auto_seed:
        from app.models import Place
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            if db.query(Place).count() == 0:
                from app.scripts.seed import seed
                from app.scripts.seed_demo_trip import seed_demo_trip
                seed()
                seed_demo_trip()
        except Exception:
            pass  # never let seeding crash startup
        finally:
            db.close()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok", "mockLLM": settings.use_mock_llm, "places": db.query(Place).count()}


@app.get("/places")
def places(db: Session = Depends(get_db)):
    return [_place_dict(p) for p in db.query(Place).all()]


@app.get("/amenities")
def amenities(db: Session = Depends(get_db)):
    return [{"id": a.id, "name": a.name, "lat": a.lat, "lon": a.lon, "type": a.type}
            for a in db.query(Amenity).all()]


@app.post("/cities/prep")
def cities_prep(body: CityPrep, db: Session = Depends(get_db)):
    """Pre-warm the reference cache for any destination (any city in India or
    worldwide). Idempotent and cheap when already cached; one-time Overpass
    fetch otherwise. Returns the resolved city slug + place count."""
    slug = city_service.ensure_city(db, body.destination)
    count = db.query(Place).filter(Place.city == slug).count()
    return {"city": slug, "places": count, "ready": count > 0}


@app.post("/trips")
def create_trip(body: TripCreate, db: Session = Depends(get_db)):
    # Resolve the destination to a plannable city (cached or fetched once).
    slug = city_service.ensure_city(db, body.destination)
    trip = Trip(destination=body.destination, start_date=body.start_date, end_date=body.end_date,
                budget_total=body.budget_total, currency=body.currency, interests=body.interests,
                hotel_place_id=body.hotel_place_id, start_time_day1=body.start_time_day1,
                pace=body.pace, group_size=body.group_size, city=slug)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    try:
        generate_trip(db, trip)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return get_trip(trip.id, db)


@app.get("/trips/{trip_id}")
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    days = db.query(Day).filter_by(trip_id=trip_id).order_by(Day.day_index).all()
    return {
        "id": trip.id, "destination": trip.destination,
        "start_date": trip.start_date, "end_date": trip.end_date,
        "budget_total": trip.budget_total, "currency": trip.currency,
        "interests": trip.interests, "hotel_place_id": trip.hotel_place_id,
        "city": trip.city,
        "days": [_day_dict(db, d) for d in days],
        "pending_changes": [_change_dict(c) for c in
                            db.query(ItineraryChange).filter_by(trip_id=trip_id, status="pending").all()],
    }


@app.get("/trips/{trip_id}/budget")
def budget(trip_id: int, target_currency: str | None = None, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    days = db.query(Day).filter_by(trip_id=trip_id).order_by(Day.day_index).all()
    per_day = []
    total = 0.0
    for d in days:
        acts = db.query(Activity).filter_by(day_id=d.id).all()
        c = sum(a.cost for a in acts)
        total += c
        per_day.append({"day_index": d.day_index, "cost": round(c, 2)})
    total += sum(b.cost for b in db.query(Booking).filter_by(trip_id=trip_id).all())
    rate, cur = 1.0, trip.currency
    if target_currency and target_currency != trip.currency:
        rate, cur = _fx(trip.currency, target_currency), target_currency
    return {"currency": cur, "per_day": [{**p, "cost": round(p["cost"] * rate, 2)} for p in per_day],
            "total": round(total * rate, 2), "budget_total": round(trip.budget_total * rate, 2),
            "over_budget": total * rate > trip.budget_total * rate + 1e-6}


@app.post("/disruptions/inject")
def inject_disruption(body: DisruptionInject, db: Session = Depends(get_db)):
    """Phase 7 — manual button AND synthetic event flow through THIS identical path."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    day = db.query(Day).filter_by(trip_id=trip.id, day_index=body.day_index).first()
    if not day:
        raise HTTPException(404, "day not found")

    acts = db.query(Activity).filter_by(day_id=day.id).order_by(Activity.seq).all()
    planned = [_to_planned(a) for a in acts]

    tmap = {(t.from_id, t.to_id): t.duration_minutes for t in db.query(TravelTime).all()}

    def travel_fn(a, b):
        if a is None or b is None:
            return 0.0
        return tmap.get((a, b), tmap.get((b, a), 20.0))

    candidates = _schedulable_candidates(db, trip)
    n_days = len(db.query(Day).filter_by(trip_id=trip.id).all())
    day_budget = (trip.budget_total / n_days) if trip.budget_total else 1e9

    _new_day, diff = repair_day(
        activities=planned, disrupted_place_id=body.disrupted_place_id,
        candidates=candidates, travel_fn=travel_fn,
        window_end=to_min(day.end_time), day_budget=day_budget,
    )
    reason = body.reason or _default_reason(body.trigger, planned, body.disrupted_place_id)

    change = ItineraryChange(trip_id=trip.id, status="pending", reason=reason,
                             trigger=body.trigger,
                             diff={**diff, "day_index": day.day_index,
                                   "disrupted_place_id": body.disrupted_place_id})
    db.add(change)
    db.commit()
    db.refresh(change)
    return _change_dict(change)


@app.post("/trips/{trip_id}/changes/{cid}/confirm")
def confirm_change(trip_id: int, cid: int, db: Session = Depends(get_db)):
    change = db.get(ItineraryChange, cid)
    if not change or change.trip_id != trip_id:
        raise HTTPException(404, "change not found")
    if change.status != "pending":
        raise HTTPException(400, "change is not pending")

    diff = change.diff
    day = db.query(Day).filter_by(trip_id=trip_id, day_index=diff["day_index"]).first()
    removed_ids = {r["place_id"] for r in diff.get("removed", [])}
    for a in db.query(Activity).filter_by(day_id=day.id).all():
        if a.place_id in removed_ids:
            db.delete(a)
    # add newly added activities
    existing = {a.place_id for a in db.query(Activity).filter_by(day_id=day.id).all()}
    for add in diff.get("added", []):
        if add["place_id"] in existing:
            continue
        p = db.get(Place, add["place_id"])
        db.add(Activity(day_id=day.id, place_id=add["place_id"], name=add["name"],
                        start_time=add["start_time"], end_time=add["end_time"],
                        duration_minutes=p.avg_visit_minutes if p else 60, cost=add["cost"],
                        interest_tag=add.get("interest_tag", ""), seq=999,
                        lat=p.lat if p else 0.0, lon=p.lon if p else 0.0))
    # apply modified time shifts
    mod = {m["place_id"]: m for m in diff.get("modified", [])}
    for a in db.query(Activity).filter_by(day_id=day.id).all():
        if a.place_id in mod:
            to = mod[a.place_id]["to"].split("-")
            a.start_time, a.end_time = to[0], to[1]
    # renumber seq by start_time
    for i, a in enumerate(sorted(db.query(Activity).filter_by(day_id=day.id).all(),
                                 key=lambda x: x.start_time)):
        a.seq = i
    change.status = "applied"
    db.commit()
    return {"status": "applied", "stability": diff.get("stability")}


@app.post("/trips/{trip_id}/changes/{cid}/reject")
def reject_change(trip_id: int, cid: int, db: Session = Depends(get_db)):
    change = db.get(ItineraryChange, cid)
    if not change or change.trip_id != trip_id:
        raise HTTPException(404, "change not found")
    change.status = "rejected"
    db.commit()
    return {"status": "rejected"}


@app.get("/trips/{trip_id}/days/{day_index}/route")
def day_route(trip_id: int, day_index: int, db: Session = Depends(get_db)):
    """Route geometry for one day, for the map view — cache-first.

    Legs are looked up in the cached `routes` table (ingestion or a previous
    fetch); on a miss, ORS Directions is called once and persisted. Without a
    key or when ORS is unreachable, legs fall back to straight lines, so the
    map always renders. Per the plan's Phase 3 principle, this is the ONLY
    runtime code path that may call ORS, and only on a cache miss.
    """
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    day = db.query(Day).filter_by(trip_id=trip_id, day_index=day_index).first()
    if not day:
        raise HTTPException(404, "day not found")

    acts = db.query(Activity).filter_by(day_id=day.id).order_by(Activity.seq).all()
    if not acts:
        raise HTTPException(404, "day has no activities to route")

    hotel = db.get(Place, trip.hotel_place_id) if trip.hotel_place_id else None
    stops = [hotel] + [db.get(Place, a.place_id) for a in acts]

    legs, fetched = [], 0
    for a, b in zip(stops, stops[1:]):
        if not a or not b:
            continue
        if a.id == b.id:
            continue
        a_ll = [a.lon, a.lat]
        b_ll = [b.lon, b.lat]
        cached = db.query(Route).filter_by(from_id=a.id, to_id=b.id).first()
        if cached and cached.geometry and len(cached.geometry) >= 2:
            geom, was_cached = cached.geometry, True
        else:
            geom = ors_service.ors_route_cached(db, a.id, b.id, a_ll, b_ll)
            was_cached = False
            fetched += 1
        legs.append({
            "from_place_id": a.id, "to_place_id": b.id,
            "from_name": a.name, "to_name": b.name,
            "geometry": geom,
            "cached": was_cached,
        })
    return {
        "day_index": day_index,
        "mode": "foot-walking",
        "legs": legs,
        "source": "cache" if fetched == 0 else ("cache+ors" if settings.ors_api_key else "cache+fallback"),
    }


@app.get("/places/search")
def places_search(q: str, db: Session = Depends(get_db)):
    """Autocomplete over cached places (typeahead). Case-insensitive prefix/substring."""
    ql = q.strip().lower()
    if not ql:
        return []
    hits = [p for p in db.query(Place).all() if ql in p.name.lower()][:8]
    return [{"id": p.id, "name": p.name, "category": p.category, "interest_tag": p.interest_tag} for p in hits]


@app.post("/chat/add")
def chat_add(body: ChatAdd, db: Session = Depends(get_db)):
    """Resolve a free-text place, find a slot, re-validate, return a PENDING diff.
    Never applied silently — the UI shows the diff with Confirm/Reject."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")

    # 1) resolve: an exact place_id wins (chat explore selection); else name
    # match within the trip's city; else geocode a brand-new place
    ql = body.place_query.strip().lower()
    city_q = db.query(Place).filter(Place.city == trip.city) if trip.city else db.query(Place)
    place = None
    if body.place_id:
        place = db.get(Place, body.place_id)
    if place is None:
        place = next((p for p in city_q.all() if ql in p.name.lower()), None)
    if place is None:
        from app.services.geocode import geocode
        from app.services.images import image_for
        g = geocode(body.place_query, near_city=trip.destination)
        if not g:
            raise HTTPException(422, f"Could not resolve a place named '{body.place_query}'.")
        place = Place(name=g["name"], lat=g["lat"], lon=g["lon"], city=trip.city or "",
                      category="culture", interest_tag="culture", opening_hours="",
                      avg_visit_minutes=60, cost=0.0, website="", image_url=image_for(g["name"]))
        db.add(place)
        db.flush()
        # add travel times from this new place to all others (haversine estimate)
        import math
        for other in db.query(Place).all():
            if other.id == place.id:
                continue
            km = _haversine_km(place.lat, place.lon, other.lat, other.lon)
            mins = round((km / 4.8) * 60, 1)
            db.add(TravelTime(from_id=place.id, to_id=other.id, duration_minutes=mins, mode="foot-walking"))
            db.add(TravelTime(from_id=other.id, to_id=place.id, duration_minutes=mins, mode="foot-walking"))
        db.commit()

    # 2) pick the day: requested, else the day with the earliest free slot (fewest activities)
    days = db.query(Day).filter_by(trip_id=trip.id).order_by(Day.day_index).all()
    if not days:
        raise HTTPException(400, "trip has no days")
    if body.day_index:
        target = next((d for d in days if d.day_index == body.day_index), days[0])
    else:
        target = min(days, key=lambda d: db.query(Activity).filter_by(day_id=d.id).count())

    # 3) build the proposed day = existing activities + the new place appended, re-timed
    acts = db.query(Activity).filter_by(day_id=target.id).order_by(Activity.seq).all()
    tmap = {(t.from_id, t.to_id): t.duration_minutes for t in db.query(TravelTime).all()}

    def travel_fn(a, b):
        if a is None or b is None:
            return 0.0
        return tmap.get((a, b), tmap.get((b, a), 20.0))

    from app.core.scheduler import PlannedActivity
    from app.core.timeutil import to_min, to_hhmm
    before = [_to_planned(a) for a in acts]
    # append the new place after the last activity, accounting for travel
    if before:
        last = before[-1]
        arrive = to_min(last.end_time) + travel_fn(last.place_id, place.id)
    else:
        arrive = to_min(target.start_time)
    finish = arrive + place.avg_visit_minutes
    added = PlannedActivity(place_id=place.id, name=place.name, start_time=to_hhmm(arrive),
                            end_time=to_hhmm(finish), duration_minutes=place.avg_visit_minutes,
                            cost=place.cost, interest_tag=place.interest_tag, seq=len(before),
                            lat=place.lat, lon=place.lon, image_url=place.image_url)
    after = before + [added]

    # 4) re-validate the proposed day
    from app.core.validator import validate_trip
    violations = validate_trip([(target.day_index, after)], travel_fn,
                               lambda pid: (db.get(Place, pid).opening_hours if db.get(Place, pid) else ""),
                               total_budget=trip.budget_total,
                               day_budget=(trip.budget_total / max(len(days), 1)) if trip.budget_total else None)

    # 5) package a pending diff (same shape as disruptions, reused by the UI)
    diff = {
        "added": [{"place_id": added.place_id, "name": added.name, "start_time": added.start_time,
                   "end_time": added.end_time, "cost": added.cost, "interest_tag": added.interest_tag}],
        "removed": [], "modified": [],
        "stability": 100.0, "day_index": target.day_index,
        "disrupted_place_id": place.id, "violations": violations,
    }
    reason = f"Add '{place.name}' to day {target.day_index} at {added.start_time}."
    if violations:
        reason += f" ⚠ {len(violations)} conflict(s) flagged — review before confirming."
    change = ItineraryChange(trip_id=trip.id, status="pending", reason=reason,
                             trigger="chat_add", diff=diff)
    db.add(change)
    db.commit()
    db.refresh(change)
    return _change_dict(change)


@app.post("/chat/move")
def chat_move(body: ChatMove, db: Session = Depends(get_db)):
    """Move an activity to another day; re-validate; return a PENDING diff."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    act = db.query(Activity).join(Day).filter(Day.trip_id == trip.id,
                                               Activity.place_id == body.place_id).first()
    if not act:
        raise HTTPException(404, "activity not on this trip")
    target = db.query(Day).filter_by(trip_id=trip.id, day_index=body.to_day_index).first()
    if not target:
        raise HTTPException(404, "target day not found")
    place = db.get(Place, body.place_id)
    diff = {
        "added": [{"place_id": place.id, "name": place.name, "start_time": "",
                   "end_time": "", "cost": place.cost, "interest_tag": place.interest_tag}],
        "removed": [{"place_id": place.id, "name": place.name, "start_time": act.start_time,
                     "end_time": act.end_time, "cost": act.cost, "interest_tag": act.interest_tag}],
        "modified": [], "stability": 90.0, "day_index": body.to_day_index,
        "disrupted_place_id": place.id, "move_to_day": body.to_day_index,
    }
    change = ItineraryChange(trip_id=trip.id, status="pending", trigger="chat_move",
                             reason=f"Move '{place.name}' to day {body.to_day_index}.", diff=diff)
    db.add(change)
    db.commit()
    db.refresh(change)
    return _change_dict(change)


@app.post("/chat/reorder")
def chat_reorder(body: ChatReorder, db: Session = Depends(get_db)):
    """Re-sequence a day into a new order, re-time with travel buffers, re-validate,
    and return a PENDING diff (drag-to-reorder → same confirm pattern)."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    day = db.query(Day).filter_by(trip_id=trip.id, day_index=body.day_index).first()
    if not day:
        raise HTTPException(404, "day not found")
    acts = {a.place_id: a for a in db.query(Activity).filter_by(day_id=day.id).all()}
    order = [pid for pid in body.ordered_place_ids if pid in acts]
    if not order:
        raise HTTPException(422, "no matching activities to reorder")

    tmap = {(t.from_id, t.to_id): t.duration_minutes for t in db.query(TravelTime).all()}

    def travel_fn(a, b):
        return 0.0 if (a is None or b is None) else tmap.get((a, b), tmap.get((b, a), 20.0))

    from app.core.timeutil import to_min, to_hhmm
    cur = to_min(day.start_time)
    modified = []
    prev = None
    for pid in order:
        a = acts[pid]
        if prev is not None:
            cur += travel_fn(prev, pid)
        new_start, new_end = to_hhmm(cur), to_hhmm(cur + a.duration_minutes)
        if (new_start, new_end) != (a.start_time, a.end_time):
            modified.append({"place_id": pid, "name": a.name,
                             "from": f"{a.start_time}-{a.end_time}", "to": f"{new_start}-{new_end}"})
        cur += a.duration_minutes
        prev = pid

    diff = {"added": [], "removed": [], "modified": modified, "stability": 100.0,
            "day_index": body.day_index, "reordered": order}
    change = ItineraryChange(trip_id=trip.id, status="pending", trigger="chat_reorder",
                             reason=f"Reorder day {body.day_index} ({len(order)} stops) and re-time with travel buffers.",
                             diff=diff)
    db.add(change)
    db.commit()
    db.refresh(change)
    return _change_dict(change)


@app.get("/trips/{trip_id}/share")
def share_trip(trip_id: int, db: Session = Depends(get_db)):
    """Return a read-only shareable view of the trip (public link payload)."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    return {"share_id": f"trip-{trip_id}", "read_only": True, "trip": get_trip(trip_id, db)}


@app.post("/chat/explore")
def chat_explore(body: ChatExplore, db: Session = Depends(get_db)):
    """'Show more places near X' — returns ranked, TAPPABLE options (never
    scheduled directly). Cached places first; if the cache is thin, tops up
    from Overpass once (same one-time ingestion as any new city)."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")

    nl = body.near_query.strip().lower()
    scope = db.query(Place)
    if trip.city:
        scope = scope.filter(Place.city == trip.city)

    # anchor: match an existing place/activity by name, else fall back to the hotel
    anchor = None
    if nl:
        anchor = next((p for p in scope.all() if nl in p.name.lower()), None)
        if anchor is None:
            act = db.query(Activity).join(Day).filter(Day.trip_id == trip.id) \
                     .filter(Activity.name.ilike(f"%{body.near_query.strip()}%")).first()
            if act:
                anchor = db.get(Place, act.place_id)
    if anchor is None:
        anchor = db.get(Place, trip.hotel_place_id) if trip.hotel_place_id else \
            scope.first()
    if anchor is None:
        raise HTTPException(422, "Nothing to search near yet — add a place or an activity first.")

    in_plan = {a.place_id for a in db.query(Activity).join(Day)
               .filter(Day.trip_id == trip.id).all()}
    options = city_service.nearby(db, trip.city or "", anchor.lat, anchor.lon,
                                  radius_km=8.0, limit=body.limit,
                                  exclude_ids=tuple(in_plan))

    # thin cache -> one-time Overpass top-up around the anchor, then re-query
    if len(options) < 3 and settings.allow_live_ingestion and trip.city:
        try:
            city_service._seed_city_rows(db, trip.city, anchor.lat, anchor.lon,
                                         radius_m=4000, max_places=24)
            in_plan = {a.place_id for a in db.query(Activity).join(Day)
                       .filter(Day.trip_id == trip.id).all()}
            options = city_service.nearby(db, trip.city, anchor.lat, anchor.lon,
                                          radius_km=8.0, limit=body.limit,
                                          exclude_ids=tuple(in_plan))
        except Exception:
            db.rollback()  # offline: cached options (possibly none) are still returned

    return {
        "near": anchor.name,
        "options": options,
        "note": "" if options else
        "Nothing new found nearby — try another landmark or check back once the city data is cached.",
    }


@app.post("/chat/change-destination")
def chat_change_destination(body: ChatChangeDestination, db: Session = Depends(get_db)):
    """'Take me to Jaipur instead' — resolves (and if needed ingests) the new
    city, then regenerates the SAME trip in place. Deliberately immediate:
    the old plan is replaced, no pending diff, because every activity changes."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    slug = city_service.ensure_city(db, body.destination)
    if not db.query(Place).filter(Place.city == slug).count():
        raise HTTPException(422,
            f"Couldn't fetch plans for '{body.destination}' right now — try again in a moment.")
    trip.destination = body.destination
    trip.city = slug
    trip.hotel_place_id = None  # stale hotel from the old city
    db.commit()
    db.refresh(trip)
    generate_trip(db, trip)
    db.refresh(trip)
    return {"status": "regenerated", "city": slug, "trip": get_trip(trip.id, db)}


@app.post("/chat")
def chat(body: ChatMessage, db: Session = Depends(get_db)):
    """Unified conversational endpoint. Groq (or mock) classifies the free-form
    message into an action, then a deterministic handler executes it. Returns
    {kind:'diff', change} for edits (pending, needs confirm) or {kind:'answer', text}."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    days = db.query(Day).filter_by(trip_id=trip.id).order_by(Day.day_index).all()
    parsed = llm.classify_chat_action(body.message, len(days))
    action, slots = parsed["action"], parsed.get("slots", {})

    def _find_activity(name: str):
        if not name:
            return None
        nl = name.lower()
        return db.query(Activity).join(Day).filter(Day.trip_id == trip.id) \
                 .filter(Activity.name.ilike(f"%{name}%")).first() \
            or next((a for a in db.query(Activity).join(Day).filter(Day.trip_id == trip.id).all()
                     if nl in a.name.lower()), None)

    if action == "explore":
        return {"kind": "options", **chat_explore(
            ChatExplore(trip_id=trip.id, near_query=slots.get("place") or slots.get("reference", ""),
                        lang=body.lang), db)}

    if action == "change_destination":
        dest = slots.get("destination", "")
        if not dest:
            return {"kind": "answer", "text": "Where would you like to go instead? Name a city and I'll rebuild the plan there."}
        try:
            return {"kind": "regenerated", **chat_change_destination(
                ChatChangeDestination(trip_id=trip.id, destination=dest, lang=body.lang), db)}
        except HTTPException as e:
            return {"kind": "answer", "text": str(e.detail)}

    if action == "add":
        return {"kind": "diff", "change": chat_add(
            ChatAdd(trip_id=trip.id, place_query=slots.get("place", ""),
                    day_index=slots.get("to_day"), lang=body.lang), db)}

    if action == "move":
        act = _find_activity(slots.get("place", ""))
        if not act:
            return {"kind": "answer", "text": f"I couldn't find \"{slots.get('place','')}\" in your plan."}
        return {"kind": "diff", "change": chat_move(
            ChatMove(trip_id=trip.id, place_id=act.place_id,
                     to_day_index=int(slots.get("to_day") or act.day.day_index), lang=body.lang), db)}

    if action == "remove":
        act = _find_activity(slots.get("place", ""))
        if not act:
            return {"kind": "answer", "text": f"I couldn't find \"{slots.get('place','')}\" to remove."}
        diff = {"added": [], "removed": [{"place_id": act.place_id, "name": act.name,
                "start_time": act.start_time, "end_time": act.end_time, "cost": act.cost,
                "interest_tag": act.interest_tag}], "modified": [], "stability": 90.0,
                "day_index": act.day.day_index, "disrupted_place_id": act.place_id}
        change = ItineraryChange(trip_id=trip.id, status="pending", trigger="chat_remove",
                                 reason=f"Remove '{act.name}' from day {act.day.day_index}.", diff=diff)
        db.add(change); db.commit(); db.refresh(change)
        return {"kind": "diff", "change": _change_dict(change)}

    if action == "shorten":
        act = _find_activity(slots.get("place", ""))
        mins = int(slots.get("max_minutes") or 120)
        if not act:
            return {"kind": "answer", "text": f"I couldn't find \"{slots.get('place','')}\" to shorten."}
        from app.core.timeutil import to_min, to_hhmm
        new_end = to_hhmm(to_min(act.start_time) + mins)
        diff = {"added": [], "removed": [], "modified": [{"place_id": act.place_id, "name": act.name,
                "from": f"{act.start_time}-{act.end_time}", "to": f"{act.start_time}-{new_end}"}],
                "stability": 95.0, "day_index": act.day.day_index}
        change = ItineraryChange(trip_id=trip.id, status="pending", trigger="chat_shorten",
                                 reason=f"Cap '{act.name}' at {mins//60}h ({act.start_time}–{new_end}).", diff=diff)
        db.add(change); db.commit(); db.refresh(change)
        return {"kind": "diff", "change": _change_dict(change)}

    if action == "nearby":
        return {"kind": "answer", "text": llm.phrase(nearby_summary(
            ChatNearby(trip_id=trip.id, reference=slots.get("reference", "hotel"), lang=body.lang), db),
            lang=body.lang)}

    # question
    parsedq = llm.classify_intent(body.message)
    r = nl_query(NLQuery(trip_id=trip.id, question=body.message, lang=body.lang), db)
    return {"kind": "answer", "text": r["answer"], "intent": parsedq.get("intent")}


@app.post("/nl/query")
def nl_query(body: NLQuery, db: Session = Depends(get_db)):
    """Phase 8 — classify intent + extract slots (Bedrock), then a deterministic
    backend handler answers from the DB. The model never touches trip state."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        raise HTTPException(404, "trip not found")
    parsed = llm.classify_intent(body.question)
    intent, slots = parsed["intent"], parsed.get("slots", {})

    if intent == "day_plan":
        ref = slots.get("day_reference", "today")
        idx = 2 if ref == "tomorrow" else 1
        day = db.query(Day).filter_by(trip_id=trip.id, day_index=idx).first()
        acts = db.query(Activity).filter_by(day_id=day.id).order_by(Activity.seq).all() if day else []
        summary = f"On day {idx}: " + ", ".join(f"{a.name} ({a.start_time})" for a in acts) if acts else "No plan for that day."
        answer = llm.phrase(summary, lang=body.lang)
    elif intent == "near_hotel":
        hid = trip.hotel_place_id
        tmap = {(t.from_id, t.to_id): t.duration_minutes for t in db.query(TravelTime).all()}
        acts = db.query(Activity).join(Day).filter(Day.trip_id == trip.id).all()
        ranked = sorted(acts, key=lambda a: tmap.get((hid, a.place_id), 999))[:3]
        answer = llm.phrase("Closest to your hotel: " + ", ".join(a.name for a in ranked), lang=body.lang)
    elif intent == "what_if_cancel":
        answer = llm.phrase("Use the inject-disruption action to preview a minimal-diff repair before applying.", lang=body.lang)
    elif intent == "fit_check":
        answer = llm.phrase("Fit-check runs the validator against a hypothetical insertion (activity name required).", lang=body.lang)
    else:
        answer = llm.phrase("I can help with: your day plan, activities near your hotel, fit-checks, and cancellation what-ifs.", lang=body.lang)

    return {"intent": intent, "slots": slots, "answer": answer, "degraded": parsed.get("degraded", False)}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def nearby_summary(body: ChatNearby, db: Session) -> str:
    """Informational 'what's near X' text (shared by /chat nearby + tests)."""
    trip = db.get(Trip, body.trip_id)
    if not trip:
        return "Trip not found."
    tmap = {(t.from_id, t.to_id): t.duration_minutes for t in db.query(TravelTime).all()}
    if body.reference == "hotel" and trip.hotel_place_id:
        anchor = trip.hotel_place_id
    else:
        first = db.query(Activity).join(Day).filter(Day.trip_id == trip.id) \
                 .order_by(Day.day_index, Activity.seq).first()
        anchor = first.place_id if first else trip.hotel_place_id
    scope = db.query(Place)
    if trip.city:
        scope = scope.filter(Place.city == trip.city)
    cands = [p for p in scope.all()
             if p.category in ("food", "culture", "outdoor", "history", "shopping")]
    ranked = sorted(cands, key=lambda p: tmap.get((anchor, p.id), 999))[:4]
    if not ranked:
        return "Nothing cached nearby yet — try 'show me places near <landmark>'."
    return "Closest options: " + ", ".join(
        f"{p.name} (~{tmap.get((anchor, p.id), 0):.0f} min)" for p in ranked)


def _place_dict(p: Place):
    return {"id": p.id, "name": p.name, "lat": p.lat, "lon": p.lon, "category": p.category,
            "interest_tag": p.interest_tag, "opening_hours": p.opening_hours,
            "avg_visit_minutes": p.avg_visit_minutes, "cost": p.cost, "website": p.website}


def _day_dict(db: Session, d: Day):
    acts = db.query(Activity).filter_by(day_id=d.id).order_by(Activity.seq).all()
    sugg = db.query(Suggestion).filter_by(day_id=d.id).all()
    return {
        "day_index": d.day_index, "date": d.date, "start_time": d.start_time, "end_time": d.end_time,
        "activities": [{"place_id": a.place_id, "name": a.name, "start_time": a.start_time,
                        "end_time": a.end_time, "duration_minutes": a.duration_minutes, "cost": a.cost,
                        "interest_tag": a.interest_tag, "seq": a.seq, "lat": a.lat, "lon": a.lon,
                        "backups": a.backups, "image_url": a.image_url} for a in acts],
        "suggestions": [{"type": s.type, "time_window": s.time_window, "place_id": s.place_id,
                         "place_name": s.place_name, "rank": s.rank, "lat": s.lat, "lon": s.lon,
                         "website": s.website} for s in sugg],
    }


def _change_dict(c: ItineraryChange):
    return {"id": c.id, "trip_id": c.trip_id, "status": c.status, "reason": c.reason,
            "trigger": c.trigger, "diff": c.diff}


def _to_planned(a: Activity) -> PlannedActivity:
    return PlannedActivity(place_id=a.place_id, name=a.name, start_time=a.start_time,
                           end_time=a.end_time, duration_minutes=a.duration_minutes, cost=a.cost,
                           interest_tag=a.interest_tag, seq=a.seq, lat=a.lat, lon=a.lon,
                           backups=a.backups or [])


def _schedulable_candidates(db: Session, trip: Trip | None = None):
    from app.services.trip_service import SCHEDULABLE, _candidates
    return [c for c in _candidates(db, trip.city if trip else None) if c.category in SCHEDULABLE]


def _default_reason(trigger: str, planned, disrupted_id: int) -> str:
    name = next((a.name for a in planned if a.place_id == disrupted_id), "an activity")
    if trigger == "weather":
        return f"Weather alert: '{name}' is an outdoor stop likely affected — rebuilding the rest of the day around it."
    if trigger == "flight":
        return f"Flight-status change impacts timing; '{name}' and everything after it re-planned."
    return f"'{name}' was disrupted — only the affected part of the day was rebuilt."


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _fx(base: str, target: str) -> float:
    """Phase 6 currency conversion via Frankfurter (cached per call; not per page load)."""
    try:
        import httpx
        r = httpx.get(f"{settings.frankfurter_url}/latest", params={"from": base, "to": target}, timeout=5)
        return r.json()["rates"][target]
    except Exception:
        return 1.0
