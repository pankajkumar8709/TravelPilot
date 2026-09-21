"""Third POI source for thin cities: Wikipedia TEXT search around nearby towns.

Geosearch covers a 10 km disk around each probe; for spread-out cities the
interesting stops (Golden Temple's Amritsar, Hampi's ruins) can sit just past
it. This layer finds satellite towns within ~35 km via ORS-free means —
Wikipedia text search for '<town> attractions' — and resolves each hit's
coordinates with the MediaWiki API. Keyless, real-time, no hardcoding: the
towns come from Wikipedia's own geosearch around the city center.
"""
from __future__ import annotations

import httpx

WIKI_API = "https://en.wikipedia.org/w/api.php"


def nearby_town_pois(lat: float, lon: float, city: str, have_names: set[str],
                     ua: dict, need: int = 15) -> list[dict]:
    """Attractions in towns near `city`: geosearch for towns 8-30 km out, then
    text-search each town's notable places, resolving coordinates per hit."""
    out: dict[str, dict] = {}

    # 1) satellite towns from geosearch (already-known list works: pages whose
    # description says 'town/village/city in <state>') — reuse geosearch with
    # offset probes 15-30 km out
    import math
    towns: list[tuple[str, float, float]] = []
    for ang in (30, 110, 190, 270):
        rad = math.radians(ang)
        tlat = lat + 0.20 * math.cos(rad)
        tlon = lon + 0.20 * math.sin(rad) / max(math.cos(math.radians(lat)), 0.2)
        try:
            r = httpx.get(WIKI_API, params={
                "action": "query", "format": "json", "generator": "geosearch",
                "ggscoord": f"{tlat}|{tlon}", "ggsradius": 10000, "ggslimit": 10,
                "prop": "coordinates|description",
            }, headers=ua, timeout=15)
            r.raise_for_status()
            for p in ((r.json().get("query", {}) or {}).get("pages", {}) or {}).values():
                desc = (p.get("description") or "").lower()
                coords = (p.get("coordinates") or [{}])[0]
                t, la, lo = p.get("title"), coords.get("lat"), coords.get("lon")
                if not t or la is None:
                    continue
                # a settlement page (not the city itself, not an attraction)
                if desc.startswith(("town in", "city in", "village in", "municipality in",
                                    "suburb in", "neighbourhood in", "neighborhood in")):
                    towns.append((t, la, lo))
        except Exception:
            continue

    # 2) for each town, one text search for its notable places
    for town, tlat, tlon in towns[:6]:
        if len(out) >= need:
            break
        try:
            r = httpx.get(WIKI_API, params={
                "action": "query", "format": "json", "list": "search",
                "srsearch": f"{town} temple OR fort OR palace OR museum OR park",
                "srlimit": 8,
            }, headers=ua, timeout=15)
            r.raise_for_status()
            titles = [hit["title"] for hit in
                      ((r.json().get("query", {}) or {}).get("search", []) or [])
                      if hit.get("title")]
        except Exception:
            continue
        # 3) resolve coordinates for the titles in one batched call
        if not titles:
            continue
        try:
            r = httpx.get(WIKI_API, params={
                "action": "query", "format": "json", "titles": "|".join(titles[:8]),
                "prop": "coordinates|description",
            }, headers=ua, timeout=15)
            r.raise_for_status()
            pages = ((r.json().get("query", {}) or {}).get("pages", {}) or {})
        except Exception:
            continue
        for p in pages.values():
            title = p.get("title")
            coords = (p.get("coordinates") or [{}])[0]
            la, lo = coords.get("lat"), coords.get("lon")
            if not title or la is None or title.lower() in have_names:
                continue
            tl = title.lower()
            if any(w in tl for w in ("list of", "history of", "pradesh", "bengal",
                                     "constituency", "station", "institute", "university")):
                continue
            desc = (p.get("description") or "").lower()
            if desc.startswith(("town in", "city in", "village in", "suburb in",
                                "neighbourhood in", "neighborhood in", "state in")):
                continue
            if any(w in desc for w in ("temple", "fort", "palace", "mosque", "church",
                                       "gurudwara", "shrine", "monument", "tomb")):
                cat = "history"
            elif any(w in desc for w in ("park", "lake", "hill", "beach", "garden", "dam")):
                cat = "outdoor"
            else:
                cat = "culture"
            out[title] = {"name": title, "lat": float(la), "lon": float(lo),
                          "category": cat, "interest_tag": cat, "opening_hours": "",
                          "avg_visit_minutes": 60, "cost": 0.0, "website": "", "city": ""}
            if len(out) >= need:
                break
    return list(out.values())
