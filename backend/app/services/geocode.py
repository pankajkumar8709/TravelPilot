"""Nominatim geocoding (keyless) — resolve an arbitrary place name to a POI.

Used by the chat "add <place>" flow to turn free text ("IIT Delhi") into a real
lat/lon we can insert and schedule. Returns None if nothing resolves.
Nominatim requires a descriptive User-Agent and rate-limits to ~1 req/sec.
"""
from __future__ import annotations

import httpx

UA = {"User-Agent": "TravelPilot/1.0 (hackathon; travelpilot@example.com)"}


def geocode(query: str, near_city: str = "") -> dict | None:
    """Resolve `query` to {name, lat, lon}. Biases toward `near_city` if given."""
    q = f"{query}, {near_city}" if near_city else query
    try:
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
            "name": query.strip().title(),
            "lat": float(top["lat"]),
            "lon": float(top["lon"]),
            "display_name": top.get("display_name", ""),
        }
    except Exception:
        return None
