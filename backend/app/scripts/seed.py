"""Phase 3 seed loader — writes the Paris reference data into the DB and COMPUTES
the pairwise travel-time matrix + route geometry ONCE (haversine + walk speed),
so the runtime only ever reads its own DB.

Run:  cd backend && python -m app.scripts.seed
"""
from __future__ import annotations

import math

from app.db import SessionLocal, init_db
from app.models import Amenity, Place, Route, TravelTime
from app.scripts.seed_data import PARIS_AMENITIES, PARIS_PLACES

WALK_SPEED_KMH = 4.8  # average city walking speed


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def seed() -> dict:
    init_db()
    db = SessionLocal()
    try:
        # idempotent: clear reference tables
        db.query(TravelTime).delete()
        db.query(Route).delete()
        db.query(Place).delete()
        db.query(Amenity).delete()
        db.commit()

        places: list[Place] = []
        from app.services.images import image_for
        import os
        want_images = os.environ.get("SEED_IMAGES", "1") != "0"
        for (name, lat, lon, cat, tag, oh, visit, cost, site) in PARIS_PLACES:
            img = image_for(name) if want_images else ""
            p = Place(name=name, lat=lat, lon=lon, category=cat, interest_tag=tag,
                      opening_hours=oh, avg_visit_minutes=visit, cost=cost, website=site,
                      image_url=img)
            db.add(p)
            places.append(p)
        db.flush()  # assign ids

        for (name, lat, lon, typ) in PARIS_AMENITIES:
            db.add(Amenity(name=name, lat=lat, lon=lon, type=typ))

        # pairwise travel times + straight-line route geometry (computed once)
        for a in places:
            for b in places:
                if a.id == b.id:
                    continue
                km = haversine_km(a.lat, a.lon, b.lat, b.lon)
                minutes = round((km / WALK_SPEED_KMH) * 60, 1)
                db.add(TravelTime(from_id=a.id, to_id=b.id, duration_minutes=minutes, mode="foot-walking"))
                db.add(Route(from_id=a.id, to_id=b.id, geometry=[[a.lon, a.lat], [b.lon, b.lat]]))

        db.commit()
        counts = {
            "places": db.query(Place).count(),
            "amenities": db.query(Amenity).count(),
            "travel_times": db.query(TravelTime).count(),
            "routes": db.query(Route).count(),
        }
        return counts
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeded:", seed())
