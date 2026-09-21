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
    # stays are cached like any reference data; category "hotel" is never in
    # the scheduler's SCHEDULABLE set, so they never become day activities
    ("tourism", "hotel"): ("hotel", "history", 0, 0.0),
    ("tourism", "guest_house"): ("hotel", "history", 0, 0.0),
}
AMENITY_TAGS = {"toilets": "toilets", "atm": "atm", "pharmacy": "pharmacy"}

# Chat shorthand -> real category: "add a museum", "any park nearby", etc.
CATEGORY_WORDS = {
    "museum": "culture", "gallery": "culture", "monument": "history",
    "fort": "history", "palace": "history", "temple": "history",
    "park": "outdoor", "garden": "outdoor", "lake": "outdoor",
    "mall": "shopping", "market": "shopping", "zoo": "outdoor",
}


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
      node(around:{radius},{lat},{lon})["tourism"~"hotel|guest_house"];
    );
    out body;
    """
    last = None
    for url in OVERPASS_MIRRORS[:2]:  # keep worst-case latency bounded (~2x6s)
        try:
            r = httpx.post(url, data={"data": q},
                           headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
                           timeout=6)
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


def _hotel(db: Session, city: str) -> Place | None:
    """A cached hotel for the city (used as explore anchor)."""
    return db.query(Place).filter(Place.city == city, Place.category == "hotel").first()


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


def _poi_wikipedia(lat: float, lon: float, max_places: int, city_name: str = "") -> list[dict]:
    """Keyless fallback POI source: Wikipedia geosearch around a point.

    Used when every Overpass mirror refuses (some networks/regions get 504s).
    Queries the center PLUS four offsets (geosearch caps at 10 km, so big
    cities need multiple probes to gather enough POIs). Returns place dicts in
    the same shape the Overpass parser emits; categories are approximated from
    the page description, hours left empty (the scheduler treats missing hours
    as open)."""
    import math as _math
    from concurrent.futures import ThreadPoolExecutor
    # 9 probes: center + 8 compass points ~6.5 km out (geosearch caps at 10 km,
    # and hill/spread cities have sparse coverage from the center alone)
    base_d = 0.06
    probes = [(lat, lon)]
    for ang in range(0, 360, 45):
        rad = _math.radians(ang)
        probes.append((lat + base_d * _math.cos(rad),
                       lon + base_d * _math.sin(rad) / max(_math.cos(_math.radians(lat)), 0.2)))

    def _probe(plat: float, plon: float) -> dict:
        r = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query", "format": "json", "generator": "geosearch",
                "ggscoord": f"{plat}|{plon}",
                "ggsradius": 10000,  # API hard cap: >10000 errors out silently
                "ggslimit": 50,
                "prop": "coordinates|description", "inprop": "url",
            },
            headers=UA, timeout=15,
        )
        r.raise_for_status()
        return r.json()

    seen_pages: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for data in ex.map(lambda p: _probe(*p), probes):
            try:
                if data.get("error"):
                    continue
                for pid, page in ((data.get("query", {}) or {}).get("pages", {}) or {}).items():
                    seen_pages[pid] = page
            except Exception:
                continue
            if len(seen_pages) >= max(90, max_places * 4):
                break
    pages = seen_pages
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
        # skip obvious non-visitable pages: villages, stations, institutes,
        # infrastructure, region/admin pages — geosearch returns them happily
        junk_words = ("village", "suburb", "colony", "railway station",
                      "metro station", "airport", "institute", "university",
                      "college", "school", "hospital", " works", "plant",
                      "cemetery", "graveyard", "reservoir", "dam", "refinery",
                      "constituency", "high court", "court complex", "vidyapith",
                      "pradesh", "bengal", "nadu", "geography of", "history of",
                      "culture of", "list of", "economy of", "politics of")
        if any(w in tl for w in junk_words):
            continue
        desc_full = (p.get("description") or "").lower()
        if desc_full.rstrip().startswith(("state in", "union territory", "city in",
                                          "town in", "village in", "suburb in",
                                          "municipality in", "region in", "district in",
                                          "neighbourhood in", "neighborhood in",
                                          "locality in", "subdivision in")):
            continue
        # drop the bare city article itself ('Shimla'), but KEEP places that
        # merely mention the city ('Mall Road, Shimla')
        cl = city_name.strip().lower()
        if cl and tl == cl:
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


def _is_low_quality_name(name: str) -> bool:
    """OSM is full of unnamed/generic shop rows ('city style', 'bansal arcade').
    They read as noise in explore options, so drop the obviously generic ones."""
    n = name.strip().lower()
    if len(n) <= 3:
        return True
    generic = {"shopping", "complex", "plaza", "mall", "market", "centre", "center", "store", "shop"}
    return all(w in generic for w in n.split())


def _poi_ors(lat: float, lon: float, max_places: int) -> list[dict]:
    """Second POI source: ORS Places (category 280 = tourism attractions),
    from the ORS_API_KEY the project already holds. Fills the gap when
    Wikipedia geosearch is thin (hill towns, tier-2/3 cities)."""
    if not settings.ors_api_key:
        return []
    from concurrent.futures import ThreadPoolExecutor

    def _q(cat: int) -> list[dict]:
        try:
            r = httpx.post(
                f"{settings.ors_base_url}/pois",
                headers={"Authorization": settings.ors_api_key, **UA},
                json={"request": "pois", "limit": 500,
                      "geometry": {"geojson": {"type": "Point", "coordinates": [lon, lat]},
                                   "buffer": 2000},  # API hard cap 2000 m
                      "filters": {"category_ids": [cat]}},
                timeout=25,
            )
            r.raise_for_status()
        except Exception:
            return []  # quota/down: skip, Wikipedia-only stays workable
        out = []
        for f in r.json().get("features", []):
            t = f.get("properties", {}).get("osm_tags", {}) or {}
            name = t.get("name")
            if not name:
                continue
            coords = f.get("geometry", {}).get("coordinates", [None, None])
            if not coords or coords[0] is None:
                continue
            lon_, lat_ = coords[:2]
            tag = "culture" if cat == 280 else "outdoor"
            out.append({"name": str(name).title(), "lat": float(lat_), "lon": float(lon_),
                        "category": tag, "interest_tag": tag,
                        "opening_hours": t.get("opening_hours", ""),
                        "avg_visit_minutes": 60, "cost": 0.0,
                        "website": t.get("website", ""), "city": ""})
        return out

    # 280 = sightseeing/attractions; 130 = parks/green if supported
    cats = [280]
    seen: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(cats)) as ex:
        for batch in ex.map(_q, cats):
            for p in batch:
                if p["name"] not in seen:
                    seen[p["name"]] = p
    return list(seen.values())[:max_places]


def _seed_city_rows(db: Session, city: str, lat: float, lon: float, radius_m: int,
                    max_places: int) -> int:
    """Fetch + write reference rows for `city`. Returns places written."""
    try:
        data = _overpass(lat, lon, radius_m)
    except Exception:
        # All Overpass mirrors refused (network-level block). Fall back to the
        # keyless Wikipedia geosearch, topped up with ORS category search when
        # Wikipedia is thin. POIs carry their category through so the parser
        # below keeps them — a name-only element would be skipped.
        db.rollback()
        pois = _poi_wikipedia(lat, lon, max_places, city_name=city)
        if len(pois) < max_places:
            try:
                have = {p["name"].lower() for p in pois}
                for p in _poi_ors(lat, lon, max_places - len(pois) + 10):
                    if p["name"].lower() not in have:
                        pois.append(p)
            except Exception:
                pass  # ORS down/unavailable: Wikipedia-only is still workable
        if len(pois) < max_places:
            # still thin: probe neighboring towns (same state) for day-trip stops
            try:
                from app.services.wiki_search import nearby_town_pois
                have = {p["name"].lower() for p in pois}
                for p in nearby_town_pois(lat, lon, city, have, UA,
                                          need=max_places - len(pois)):
                    pois.append(p)
            except Exception:
                pass
        data = {"elements": [
            {"lat": p["lat"], "lon": p["lon"],
             "tags": {"name": p["name"], "_category": p["category"],
                      "_interest_tag": p["interest_tag"]}}
            for p in pois
        ]}

    activities, amenities = [], []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or "lat" not in el or "lon" not in el:
            continue
        if _is_low_quality_name(name):
            continue
        cat = tag_i = None
        visit, cost = 60, 0.0
        if tags.get("_category"):
            # pre-classified (Wikipedia fallback): use the carried category
            cat, tag_i = tags["_category"], tags.get("_interest_tag", tags["_category"])
        else:
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

    # No hotel rows (Wikipedia fallback can't supply them, and some networks
    # block every Overpass mirror): synthesize placeholder stays near the city
    # center so day-end stay suggestions and the chat 'near my hotel' anchor
    # always have something real to point at. Links go to a live maps search.
    if not db.query(Place).filter(Place.city == city, Place.category == "hotel").first():
        maps_link = ("https://www.google.com/maps/search/?api=1&query=hotels+near+" + city)
        for k, (dl, dg, label) in enumerate([
            (0.004, 0.004, f"Hotel {city.title()} Central"),
            (-0.005, 0.003, f"{city.title()} Grand Stay"),
            (0.003, -0.005, f"Hotel {city.title()} Residency"),
        ]):
            dup = db.query(Place).filter(Place.city == city, Place.name == label).first()
            if not dup:
                db.add(Place(name=label, lat=lat + dl, lon=lon + dg, city=city,
                             category="hotel", interest_tag="history", opening_hours="",
                             avg_visit_minutes=0, cost=0.0, website=maps_link, image_url=""))
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
    Raises RuntimeError with a user-safe message when the destination cannot be
    made plannable AND is not the seeded default — callers decide whether to
    fall back (intake can degrade; chat change-destination must NOT silently
    rebuild the trip in the wrong city).
    """
    slug = _slug(destination)

    if db.query(Place.id).filter(Place.city == slug).first():
        return slug

    if not settings.allow_live_ingestion:
        if slug == default_city_slug():
            return slug
        raise RuntimeError(
            f"Live data fetching is off, so '{destination.title()}' can't be planned right now.")

    gc = geocode_city(destination)
    if not gc:
        if slug == default_city_slug():
            return default_city_slug()
        raise RuntimeError(
            f"Couldn't find '{destination.title()}' — check the spelling, or try a nearby city.")

    try:
        wrote = _seed_city_rows(db, slug, gc["lat"], gc["lon"], radius_m=8000, max_places=40)
    except Exception:
        db.rollback()
        if slug == default_city_slug():
            return default_city_slug()
        raise RuntimeError(
            f"Couldn't fetch plans for '{destination.title()}' right now — try again in a moment.")

    # Too few plannable places (state/region name geocoded to a rural centroid,
    # dead POI source) -> treat as failure so callers fail fast instead of
    # building an empty plan that spins forever in the UI. Also remove the
    # rows this attempt wrote (e.g. synthesized hotels) so failed cities don't
    # leave phantom data behind.
    plannable = db.query(Place.id).filter(
        Place.city == slug, Place.category.in_(("culture", "outdoor", "history", "shopping", "nightlife"))
    ).count()
    if plannable < 5 and slug != default_city_slug():
        db.query(Place).filter(Place.city == slug).delete()
        db.commit()
        raise RuntimeError(
            f"Not enough plannable places found for '{destination.title()}' — "
            "try a major city near you instead.")

    return slug


def default_city_slug() -> str:
    """Slug of the offline-seeded demo city."""
    return _slug("Delhi")
