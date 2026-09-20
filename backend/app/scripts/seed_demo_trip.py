"""Phase 2 walking-skeleton seed — guarantees ONE demo trip exists.

The plan's Phase 2 wants a single hardcoded trip the deployed dashboard can render
before any real logic/interaction. We generate trips live (POST /trips), but this
also stamps a fixed demo trip so `GET /trips/1` always returns a full itinerary
end-to-end — the exact "open the URL and see a real (if fake) itinerary" check.

Run AFTER app.scripts.seed (which loads the reference data):
  python -m app.scripts.seed
  python -m app.scripts.seed_demo_trip
"""
from __future__ import annotations

from app.db import SessionLocal, init_db
from app.models import Trip
from app.services.trip_service import generate_trip


def seed_demo_trip() -> dict:
    init_db()
    db = SessionLocal()
    try:
        # idempotent: drop any existing demo trip so re-running is clean
        for t in db.query(Trip).filter(Trip.destination == "Delhi").all():
            db.delete(t)
        db.commit()

        trip = Trip(
            destination="Delhi",
            start_date="2026-09-25",
            end_date="2026-09-27",
            budget_total=6000.0,
            currency="INR",
            interests=["history", "culture", "outdoor"],
            hotel_place_id=None,
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)
        generate_trip(db, trip)
        db.refresh(trip)
        days = len(trip.days)
        acts = sum(len(d.activities) for d in trip.days)
        return {"trip_id": trip.id, "days": days, "activities": acts,
                "check": f"GET /trips/{trip.id} now returns a full itinerary"}
    finally:
        db.close()


if __name__ == "__main__":
    print("Demo trip seeded:", seed_demo_trip())
