"""Geocoding — resolve an arbitrary place name to a POI (keyless-first).

Used by the chat "add <place>" flow to turn free text ("IIT Delhi") into a real
lat/lon we can insert and schedule. Layered providers, in order:

1. Nominatim (keyless)  — richest data, but 403-blocks some networks
2. ORS geocode          — uses the ORS_API_KEY the project already holds
3. Photon (keyless)     — Komoot's OSM search, independent infrastructure

When the caller supplies the trip's city center (near_lat/near_lon), results
are biased toward it AND validated: anything landing more than 150 km away is
rejected, so "Nucleus Mall" in a Ranchi trip can't silently resolve to a mall
in Montana. Returns None only if no provider yields a nearby hit — the chat
then answers honestly instead of adding a wrong place.
"""
from __future__ import annotations

import math

import httpx

from app.config import settings

UA = {"User-Agent": "TravelPilot/1.0 (hackathon; travelpilot@example.com)"}
MAX_RADIUS_KM = 150.0  # "near the trip's city" sanity bound


def geocode(query: str, near_city: str = "",
            near_lat: float | None = None, near_lon: float | None = None) -> dict | None:
    """Resolve `query` to {name, lat, lon}, biased/validated near the city center."""
    q = f"{query}, {near_city}" if near_city else query
    biased = near_lat is not None and near_lon is not None
    for provider in (_geocode_nominatim, _geocode_ors, _geocode_photon):
        try:
            res = provider(q, near_lat, near_lon) if biased else provider(q, None, None)
        except Exception:
            res = None
        if res and (not biased or
                    _haversine_km(near_lat, near_lon, res["lat"], res["lon"]) <= MAX_RADIUS_KM):
            return res
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _geocode_nominatim(q: str, lat, lon) -> dict | None:
    r = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": q, "format": "json", "limit": 1, "addressdetails": 0},
        headers=UA, timeout=15,
    )
    r.raise_for_status()
    results = r.json()
    if not results:
        return None
    top = results[0]
    return {
        "name": _clean_name(q),
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name", ""),
    }


def _geocode_ors(q: str, lat, lon) -> dict | None:
    if not settings.ors_api_key:
        return None
    params = {"text": q, "size": 1}
    if lat is not None and lon is not None:
        # circle bias keeps results inside the trip's region
        params.update({"boundary.circle.lat": lat, "boundary.circle.lon": lon,
                       "boundary.circle.radius": MAX_RADIUS_KM})
    r = httpx.get(
        f"{settings.ors_base_url}/geocode/search",
        params=params,
        headers={"Authorization": settings.ors_api_key, **UA},
        timeout=15,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        return None
    lon_, lat_ = feats[0]["geometry"]["coordinates"][:2]
    return {
        "name": _clean_name(q),
        "lat": float(lat_),
        "lon": float(lon_),
        "display_name": feats[0].get("properties", {}).get("label", q),
    }


def _geocode_photon(q: str, lat, lon) -> dict | None:
    params = {"q": q, "limit": 1}
    if lat is not None and lon is not None:
        params.update({"lat": lat, "lon": lon})
    r = httpx.get(
        "https://photon.komoot.io/api/",
        params=params,
        headers=UA, timeout=15,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        return None
    lon_, lat_ = feats[0]["geometry"]["coordinates"][:2]
    props = feats[0].get("properties", {})
    return {
        "name": _clean_name(q),
        "lat": float(lat_),
        "lon": float(lon_),
        "display_name": props.get("name", q),
    }


def _clean_name(q: str) -> str:
    """'nucleus mall, Ranchi' -> 'Nucleus Mall' (drop the city bias tail)."""
    return q.split(",")[0].strip().title()
