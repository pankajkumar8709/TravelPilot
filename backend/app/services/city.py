"""City service — generate plans for ANY city, not just the seeded one.

Follows the plan's data-sourcing principle, extended from one city to many:
reference data (places, amenities, travel times) for a city is fetched ONCE
from keyless OpenStreetMap endpoints (Overpass + Nominatim), cached in the DB
forever, and never re-fetched at runtime. Disruption/weather signals remain
the only live-poll category.

`ensure_city` is idempotent and cheap when the city is already cached: one
indexed lookup on Place.city, zero network calls. It fetches only on a miss
and honors ALLOW_LIVE_INGESTION=false for strictly offline operation (tests,
air-gapped demos) — in that mode an unknown city falls back to the default
seeded city rather than failing.
"""
from __future__ import annotations

import math

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Amenity, Place, Route, TravelTime

WALK_SPEED_KMH = 4.8
UA = {"User-Agent": "TravelPilot/1.0 (hackathon project; contact: travelpilot@example.com)"}

# Mirrors tried in order (same list as the Phase 3 ingest script).
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# OSM tag -> (category, interest_tag, default visit minutes, rough per-person cost INR)
ACTIVITY_TAGS = {
    ("tourism", "museum"): ("culture", "culture", 90, 200.0),
    ("tourism", "gallery"): ("culture", "culture", 60, 150.0),
    ("tourism", "attraction"): ("outdoor", "outdoor", 60, 0.0),
    ("tourism", "viewpoint"): ("outdoor", "outdoor", 30, 0.0),
    ("tourism", "zoo"): ("outdoor", "outdoor", 150, 400.0),
    ("historic", "monument"): ("history", "history", 45, 100.0),
    ("historic", "memorial"): ("history", "history", 30, 0.0),
    ("historic", "castle"): ("history", "history", 90, 250.0),
    ("historic", "fort"): ("history", "history", 90, 250.0),
    ("historic", "ruins"): ("history", "history", 60, 100.0),
    ("historic", "tomb"): ("history", "history", 45, 100.0),
    ("historic", "palace"): ("history", "history", 75, 150.0),
    ("leisure", "park"): ("outdoor", "outdoor", 60, 0.0),
    ("leisure", "garden"): ("outdoor", "outdoor", 45, 0.0),
    ("amenity", "place_of_worship"): ("history", "history", 40, 0.0),
    ("shop", "mall"): ("shopping", "shopping", 75, 0.0),
}
AMENITY_TAGS = {"toilets": "toilets", "atm": "atm", "pharmacy": "pharmacy"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _slug(name: str) -> str:
    """Canonical city key: lowercase, first comma-segment, alnum only."""
    base = name.split(",")[0].strip().lower()
    return "".join(c for c in base if c.isalnum()) or base


def geocode_city(name: str) -> dict | None:
    """Resolve a city name to {name, lat, lon} via layered providers:
    Nominatim (keyless) -> ORS geocode (uses the existing ORS_API_KEY) ->
    Photon (keyless). Nominatim rate-limits/blocks some IPs (403), so the
    fallbacks keep any-city generation working everywhere."""
    for provider in (_geocode_nominatim, _geocode_ors, _geocode_photon):
        try:
            res = provider(name)
        except Exception:
            res = None
        if res:
            return res
    return None


def _geocode_nominatim(name: str) -> dict | None:
    r = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": name, "format": "json", "limit": 1},
        headers=UA, timeout=15,
    )
    r.raise_for_status()
    res = r.json()
    if not res:
        return None
    top = res[0]
    return {"name": name.strip(), "lat": float(top["lat"]), "lon": float(top["lon"]),
            "display_name": top.get("display_name", "")}


def _geocode_ors(name: str) -> dict | None:
    if not settings.ors_api_key:
        return None
    r = httpx.get(
        f"{settings.ors_base_url}/geocode/search",
        params={"text": name, "size": 1},
        headers={"Authorization": settings.ors_api_key, **UA}, timeout=15,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        return None
    lon, lat = feats[0]["geometry"]["coordinates"][:2]
    label = feats[0].get("properties", {}).get("label", name)
    return {"name": name.strip(), "lat": float(lat), "lon": float(lon), "display_name": label}


def _geocode_photon(name: str) -> dict | None:
    r = httpx.get(
        "https://photon.komoot.io/api/",
        params={"q": name, "limit": 1},
        headers=UA, timeout=15,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        return None
    lon, lat = feats[0]["geometry"]["coordinates"][:2]
    return {"name": name.strip(), "lat": float(lat), "lon": float(lon),
            "display_name": feats[0].get("properties", {}).get("name", name)}


def _overpass(lat: float, lon: float, radius: int) -> dict:
    q = f"""
    [out:json][timeout:60];
    (
      node(around:{radius},{lat},{lon})["tourism"~"museum|gallery|attraction|viewpoint|zoo"];
      node(around:{radius},{lat},{lon})["historic"~"monument|memorial|castle|fort|ruins|tomb|palace"];
      node(around:{radius},{lat},{lon})["leisure"~"park|garden"];
      node(around:{radius},{lat},{lon})["amenity"="place_of_worship"];
      node(around:{radius},{lat},{lon})["amenity"~"restaurant|cafe|toilets|atm|pharmacy"];
      node(around:{radius},{lat},{lon})["shop"="mall"];
    );
    out body;
    """
    last = None
    for url in OVERPASS_MIRRORS:
        try:
            r = httpx.post(url, data={"data": q},
                           headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
                           timeout=20)
            if r.status_code == 200:
                return r.json()
            last = f"{url} -> {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = f"{url} -> {e}"
    raise RuntimeError(f"all Overpass mirrors refused; last: {last}")


def _city_center(db: Session, city: str) -> tuple[float, float] | None:
    """Rough city center from any cached place of that city."""
    p = db.query(Place).filter(Place.city == city).first()
    return (p.lat, p.lon) if p else None


def nearby(db: Session, city: str, lat: float, lon: float, radius_km: float = 5.0,
           categories: tuple[str, ...] = ("culture", "outdoor", "history", "shopping", "nightlife"),
           exclude_ids: tuple[int, ...] = (), limit: int = 6) -> list[dict]:
    """Cached places of `city` nearest to a point — powers 'show more near X'."""
    exclude = set(exclude_ids)
    hits = []
    for p in db.query(Place).filter(Place.city == city, Place.category.in_(categories)).all():
        if p.id in exclude:
            continue
        d = haversine_km(lat, lon, p.lat, p.lon)
        if d <= radius_km:
            hits.append((d, p))
    hits.sort(key=lambda t: t[0])
    return [{"place_id": p.id, "name": p.name, "category": p.category,
             "interest_tag": p.interest_tag, "distance_km": round(d, 1),
             "cost": p.cost, "avg_visit_minutes": p.avg_visit_minutes,
             "image_url": p.image_url, "website": p.website, "lat": p.lat, "lon": p.lon}
            for d, p in hits[:limit]]


def _poi_wikipedia(lat: float, lon: float, max_places: int) -> list[dict]:
    """Keyless fallback POI source: Wikipedia geosearch around a point.

    Used when every Overpass mirror refuses (some networks/regions get 504s).
    Returns place dicts in the same shape the Overpass parser emits; categories
    are approximated from the page description, hours left empty (the scheduler
    treats missing hours as open)."""
    r = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query", "format": "json", "generator": "geosearch",
            "ggscoord": f"{lat}|{lon}", "ggsradius": 11000, "ggslimit": max(10, max_places * 3),
            "prop": "coordinates|description", "inprop": "url",
        },
        headers=UA, timeout=20,
    )
    r.raise_for_status()
    pages = (r.json().get("query", {}) or {}).get("pages", {})
    out = []
    for p in pages.values():
        title = p.get("title")
        coords = (p.get("coordinates") or [{}])[0]
        lat_p, lon_p = coords.get("lat"), coords.get("lon")
        if not title or lat_p is None or lon_p is None:
            continue
        # skip administrative/region articles that aren't visitable stops
        tl = title.lower()
        if tl.rstrip().endswith(("district", "division", "tehsil", "metropolitan area")):
            continue
        desc = (p.get("description") or "").lower()
        if any(w in desc for w in ("park", "garden", "lake", "hill")):
            cat, tag = "outdoor", "outdoor"
        elif any(w in desc for w in ("shop", "market", "bazaar")):
            cat, tag = "shopping", "shopping"
        elif any(w in desc for w in ("mosque", "temple", "church", "gurdwara", "shrine")):
            cat, tag = "history", "history"
        elif any(w in desc for w in ("museum", "gallery", "theatre", "hall")):
            cat, tag = "culture", "culture"
        else:
            cat, tag = "culture", "culture"
        out.append({
            "name": title, "lat": float(lat_p), "lon": float(lon_p),
            "category": cat, "interest_tag": tag, "opening_hours": "",
            "avg_visit_minutes": 60, "cost": 0.0, "website": "", "city": "",
        })
    return out[:max_places]


def _seed_city_rows(db: Session, city: str, lat: float, lon: float, radius_m: int,
                    max_places: int) -> int:
    """Fetch + write reference rows for `city`. Returns places written."""
    try:
        data = _overpass(lat, lon, radius_m)
    except Exception:
        # All Overpass mirrors refused (network-level block). Fall back to the
        # keyless Wikipedia geosearch so any-city generation still works.
        db.rollback()
        data = {"elements": [
            {"lat": p["lat"], "lon": p["lon"], "tags": {"name": p["name"]}}
            for p in _poi_wikipedia(lat, lon, max_places)
        ]}

    activities, amenities = [], []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or "lat" not in el or "lon" not in el:
            continue
        cat = tag_i = None
        visit, cost = 60, 0.0
        for (k, v), meta in ACTIVITY_TAGS.items():
            if tags.get(k) == v:
                cat, tag_i, visit, cost = meta
                break
        if cat is None:
            am = tags.get("amenity")
            if am in AMENITY_TAGS:
                amenities.append({"name": name, "lat": el["lat"], "lon": el["lon"],
                                  "type": AMENITY_TAGS[am], "city": city})
            continue
        activities.append({
            "name": name, "lat": el["lat"], "lon": el["lon"], "category": cat,
            "interest_tag": tag_i, "opening_hours": tags.get("opening_hours", ""),
            "avg_visit_minutes": visit, "cost": cost,
            "website": tags.get("website", tags.get("contact:website", "")),
            "city": city,
        })

    # round-robin across categories so cafés can't crowd out monuments
    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for a in activities:
        by_cat[a["category"]].append(a)
    sched_cats = [c for c in by_cat if c not in ("food", "hotel")]
    ordered_cats = sched_cats + [c for c in ("food", "hotel") if c in by_cat]
    balanced: list = []
    idx = 0
    while len(balanced) < max_places and any(by_cat.values()):
        cat = ordered_cats[idx % len(ordered_cats)]
        if by_cat[cat]:
            balanced.append(by_cat[cat].pop(0))
        idx += 1
        if idx > max_places * max(len(ordered_cats), 1):
            break
    activities = balanced

    from app.services.images import image_for
    from concurrent.futures import ThreadPoolExecutor
    place_rows = []
    fresh = []
    for a in activities:
        dup = db.query(Place).filter(Place.city == city, Place.name == a["name"]).first()
        if dup:
            place_rows.append(dup)
        else:
            fresh.append(a)
    # photos in parallel — sequential Wikipedia lookups dominated ingestion time
    if fresh:
        with ThreadPoolExecutor(max_workers=10) as ex:
            imgs = list(ex.map(lambda a: image_for(a["name"]), fresh))
        for a, img in zip(fresh, imgs):
            p = Place(image_url=img, **a)
            db.add(p)
            place_rows.append(p)
    for am in amenities[:50]:
        dup = db.query(Amenity).filter(Amenity.city == city, Amenity.name == am["name"]).first()
        if not dup:
            db.add(Amenity(**am))
    db.flush()

    # pairwise travel times + straight-line routes within this city only
    all_city_places = db.query(Place).filter(Place.city == city).all()
    have = {(t.from_id, t.to_id) for t in db.query(TravelTime).all()}
    for a in all_city_places:
        for b in all_city_places:
            if a.id == b.id or (a.id, b.id) in have:
                continue
            km = haversine_km(a.lat, a.lon, b.lat, b.lon)
            minutes = round((km / WALK_SPEED_KMH) * 60, 1)
            db.add(TravelTime(from_id=a.id, to_id=b.id, duration_minutes=minutes,
                              mode="foot-walking"))
            db.add(Route(from_id=a.id, to_id=b.id,
                         geometry=[[a.lon, a.lat], [b.lon, b.lat]]))

    db.commit()
    return len(place_rows)


def ensure_city(db: Session, destination: str) -> str:
    """Make `destination` plannable and return the city slug actually used.

    Cached city  -> no-op (one indexed lookup).
    Unknown city -> live one-time ingestion (if ALLOW_LIVE_INGESTION), else or
                    on failure -> fall back to the default seeded city.
    """
    slug = _slug(destination)

    if db.query(Place.id).filter(Place.city == slug).first():
        return slug

    if not settings.allow_live_ingestion:
        return default_city_slug()

    gc = geocode_city(destination)
    if not gc:
        return default_city_slug()  # offline / unknown name: fall back to the seed

    try:
        _seed_city_rows(db, slug, gc["lat"], gc["lon"], radius_m=8000, max_places=40)
    except Exception:
        db.rollback()
        return default_city_slug()

    return slug


def default_city_slug() -> str:
    """Slug of the offline-seeded demo city."""
    return _slug("Delhi")
