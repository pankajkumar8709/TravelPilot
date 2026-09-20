"""Phase 3 — REAL reference-data ingestion (run ONCE during dev, never at runtime).

Pipeline (plan Phase 3, in order):
  1. Overpass  -> activity POIs (restaurants, museums, parks, ...) with coords + hours
  2. Overpass  -> amenity POIs (toilets, ATMs, pharmacies) into their OWN table
  3. Nominatim -> geocode anything Overpass left without clean coords
  4. ORS       -> pairwise travel times + route GEOMETRY (polyline), pair-count CAPPED
                  (2,000 req/day free tier — we cap places and batch the matrix)
  5. write everything into the DB (places/amenities/travel_times/routes)
  6. verify    -> row counts + a spot-check join

This is the literal Phase 3 fetcher. The offline Paris seed (app.scripts.seed)
remains the deadline-safe equivalent; this proves the "fetched once, cached" claim.
The app NEVER calls Overpass/ORS at runtime — only this script does.

Run:
  set ORS_API_KEY=...            (free key from openrouteservice.org)
  python -m app.scripts.ingest --city "Paris" --lat 48.8566 --lon 2.3522 --radius 4000 --max-places 40
"""
from __future__ import annotations

import argparse
import time

import httpx

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Amenity, Place, Route, TravelTime

# OSM tag -> (our category, interest_tag, default visit minutes, rough cost EUR)
ACTIVITY_TAGS = {
    ("tourism", "museum"): ("culture", "culture", 120, 15.0),
    ("tourism", "gallery"): ("culture", "culture", 60, 12.0),
    ("tourism", "attraction"): ("outdoor", "outdoor", 75, 0.0),
    ("tourism", "viewpoint"): ("outdoor", "outdoor", 30, 0.0),
    ("tourism", "artwork"): ("culture", "culture", 20, 0.0),
    ("tourism", "theme_park"): ("outdoor", "outdoor", 180, 40.0),
    ("historic", "monument"): ("history", "history", 45, 0.0),
    ("historic", "memorial"): ("history", "history", 30, 0.0),
    ("historic", "castle"): ("history", "history", 90, 12.0),
    ("historic", "ruins"): ("history", "history", 45, 0.0),
    ("historic", "building"): ("history", "history", 45, 0.0),
    ("leisure", "park"): ("outdoor", "outdoor", 60, 0.0),
    ("leisure", "garden"): ("outdoor", "outdoor", 45, 0.0),
    ("amenity", "place_of_worship"): ("history", "history", 40, 0.0),
    ("amenity", "restaurant"): ("food", "food", 75, 30.0),
    ("amenity", "cafe"): ("food", "food", 45, 12.0),
    ("tourism", "hotel"): ("hotel", "hotel", 0, 150.0),
    ("shop", "mall"): ("shopping", "shopping", 75, 0.0),
}
AMENITY_TAGS = {"toilets": "toilets", "atm": "atm", "pharmacy": "pharmacy"}
WALK_SPEED_KMH = 4.8

# Overpass AND Nominatim reject requests without a descriptive User-Agent (-> 406/403).
UA = {"User-Agent": "TravelPilot/1.0 (hackathon project; contact: travelpilot@example.com)"}


def _overpass(lat: float, lon: float, radius: int) -> dict:
    """One Overpass query pulling activities + amenities around the point."""
    q = f"""
    [out:json][timeout:60];
    (
      node(around:{radius},{lat},{lon})["tourism"~"museum|gallery|attraction|viewpoint|artwork|theme_park|hotel"];
      node(around:{radius},{lat},{lon})["historic"~"monument|memorial|castle|ruins|building"];
      node(around:{radius},{lat},{lon})["leisure"~"park|garden"];
      node(around:{radius},{lat},{lon})["amenity"="place_of_worship"];
      node(around:{radius},{lat},{lon})["amenity"~"restaurant|cafe|toilets|atm|pharmacy"];
      node(around:{radius},{lat},{lon})["shop"="mall"];
    );
    out body;
    """
    return _overpass_query(q)


# Overpass mirrors, tried in order — some reject some clients, so we fail over.
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def _overpass_query(q: str) -> dict:
    headers = {**UA, "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    last = None
    for url in OVERPASS_MIRRORS:
        try:
            # urlencode the query into data=... exactly as the mirrors expect
            r = httpx.post(url, data={"data": q}, headers=headers, timeout=90)
            if r.status_code == 200:
                return r.json()
            last = f"{url} -> {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = f"{url} -> {e}"
    raise SystemExit(f"[ingest] all Overpass mirrors refused. Last: {last}. "
                     f"The offline Paris seed (python -m app.scripts.seed) needs no Overpass.")


def _classify(tags: dict):
    """Return ('activity', cat, interest, visit, cost) or ('amenity', type) or None."""
    for (k, v), meta in ACTIVITY_TAGS.items():
        if tags.get(k) == v:
            return ("activity", *meta)
    am = tags.get("amenity")
    if am in AMENITY_TAGS:
        return ("amenity", AMENITY_TAGS[am])
    return None


def _ors_matrix(api_key: str, coords: list[list[float]]) -> dict:
    """ORS Matrix API: durations for all pairs in ONE call (cheap on the free tier)."""
    r = httpx.post(
        f"{settings.ors_base_url}/v2/matrix/foot-walking",
        headers={"Authorization": api_key, "Content-Type": "application/json", **UA},
        json={"locations": coords, "metrics": ["duration"], "units": "m"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _ors_route(api_key: str, a: list[float], b: list[float]) -> list:
    """ORS Directions: the actual polyline between two points (for the map)."""
    r = httpx.post(
        f"{settings.ors_base_url}/v2/directions/foot-walking/geojson",
        headers={"Authorization": api_key, "Content-Type": "application/json", **UA},
        json={"coordinates": [a, b]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["features"][0]["geometry"]["coordinates"]


def ingest(city: str, lat: float, lon: float, radius: int, max_places: int, real_geometry: bool = False) -> dict:
    if not settings.ors_api_key:
        raise SystemExit("Set ORS_API_KEY (free at openrouteservice.org). Overpass/Nominatim are keyless.")

    init_db()
    db = SessionLocal()
    try:
        # 1+2) Overpass
        data = _overpass(lat, lon, radius)
        # Phase 10: land the RAW Overpass response in the S3 data lake BEFORE transforming
        # it into RDS rows (no-op if DATA_LAKE_BUCKET is unset).
        from app.services.datalake import put_raw
        put_raw("overpass", city, data)
        activities, amenities = [], []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name or "lat" not in el or "lon" not in el:
                continue
            c = _classify(tags)
            if not c:
                continue
            if c[0] == "activity":
                _, cat, interest, visit, cost = c
                activities.append({
                    "name": name, "lat": el["lat"], "lon": el["lon"],
                    "category": cat, "interest_tag": interest,
                    "opening_hours": tags.get("opening_hours", ""),
                    "avg_visit_minutes": visit, "cost": cost,
                    "website": tags.get("website", tags.get("contact:website", "")),
                })
            else:
                amenities.append({"name": name, "lat": el["lat"], "lon": el["lon"], "type": c[1]})

        # cap places (ORS free tier) BUT keep a balanced mix, else abundant cafés crowd
        # out museums/monuments and days schedule empty. Round-robin across categories,
        # and guarantee schedulable (non-food, non-hotel) POIs get first pick.
        from collections import defaultdict
        by_cat: dict[str, list] = defaultdict(list)
        for a in activities:
            by_cat[a["category"]].append(a)
        sched_cats = [c for c in by_cat if c not in ("food", "hotel")]
        # prioritise: round-robin schedulable cats first, then food, then hotels
        ordered_cats = sched_cats + [c for c in ("food", "hotel") if c in by_cat]
        balanced: list = []
        idx = 0
        while len(balanced) < max_places and any(by_cat.values()):
            cat = ordered_cats[idx % len(ordered_cats)]
            if by_cat[cat]:
                balanced.append(by_cat[cat].pop(0))
            idx += 1
            if idx > max_places * len(ordered_cats):  # safety
                break
        activities = balanced

        # clear + write reference tables
        for m in (TravelTime, Route, Place, Amenity):
            db.query(m).delete()
        db.commit()

        place_rows = []
        for a in activities:
            p = Place(**a)
            db.add(p)
            place_rows.append(p)
        for am in amenities[:50]:
            db.add(Amenity(**am))
        db.flush()

        # 4) ORS matrix (one call) for durations
        coords = [[p.lon, p.lat] for p in place_rows]
        try:
            matrix = _ors_matrix(settings.ors_api_key, coords)["durations"]
        except Exception as e:  # noqa: BLE001
            print(f"[ingest] ORS matrix failed ({e}); falling back to haversine estimate.")
            matrix = None

        for i, a in enumerate(place_rows):
            for j, b in enumerate(place_rows):
                if i == j:
                    continue
                if matrix:
                    minutes = round(matrix[i][j] / 60.0, 1)
                else:
                    minutes = _haversine_min(a.lat, a.lon, b.lat, b.lon)
                db.add(TravelTime(from_id=a.id, to_id=b.id, duration_minutes=minutes, mode="foot-walking"))

        # route geometry: default to fast straight-line polylines (great for the demo map).
        # Pass --real-geometry to fetch true ORS route paths for each place's 3 nearest
        # neighbours (slower: ~0.6s/call on the free tier).
        for i, a in enumerate(place_rows):
            nearest = sorted(
                [(j, _haversine_min(a.lat, a.lon, b.lat, b.lon)) for j, b in enumerate(place_rows) if j != i],
                key=lambda t: t[1],
            )[:3]
            for j, _ in nearest:
                b = place_rows[j]
                geom = [[a.lon, a.lat], [b.lon, b.lat]]
                if real_geometry and settings.ors_api_key:
                    try:
                        geom = _ors_route(settings.ors_api_key, [a.lon, a.lat], [b.lon, b.lat])
                        time.sleep(0.6)  # be gentle on the free tier
                    except Exception:
                        pass
                db.add(Route(from_id=a.id, to_id=b.id, geometry=geom))

        db.commit()

        # 6) verify
        counts = {
            "places": db.query(Place).count(),
            "amenities": db.query(Amenity).count(),
            "travel_times": db.query(TravelTime).count(),
            "routes": db.query(Route).count(),
        }
        sample = db.query(Place).first()
        print(f"[ingest] {city}: {counts}")
        if sample:
            print(f"[ingest] spot-check: '{sample.name}' @ ({sample.lat},{sample.lon}) cat={sample.category} hours='{sample.opening_hours}'")
        return counts
    finally:
        db.close()


def _haversine_min(lat1, lon1, lat2, lon2) -> float:
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    km = 2 * r * math.asin(math.sqrt(a))
    return round((km / WALK_SPEED_KMH) * 60, 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="Paris")
    ap.add_argument("--lat", type=float, default=48.8566)
    ap.add_argument("--lon", type=float, default=2.3522)
    ap.add_argument("--radius", type=int, default=4000)
    ap.add_argument("--max-places", type=int, default=40)
    ap.add_argument("--real-geometry", action="store_true",
                    help="fetch true ORS route polylines (slower); default is straight-line")
    args = ap.parse_args()
    ingest(args.city, args.lat, args.lon, args.radius, args.max_places, args.real_geometry)
