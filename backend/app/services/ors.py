"""OpenRouteService directions client — runtime route geometry.

The plan's data-sourcing principle: reference data is fetched ONCE and cached;
the app never depends on a live external API. The `routes` table holds cached
polylines (from ingestion or a previous runtime fetch). This module is called
only on a cache miss (GET /trips/{id}/days/{n}/route), so a live ORS outage
degrades to straight-line segments — the map still renders.

Auth: the ORS key is a BACKEND secret. It lives in backend/.env as ORS_API_KEY
(free at openrouteservice.org) and must never reach the browser bundle.
"""
from __future__ import annotations

import httpx

from app.config import settings

UA = {"User-Agent": "TravelPilot/1.0 (hackathon project; contact: travelpilot@example.com)"}


def ors_route(lonlat_a: list[float], lonlat_b: list[float]) -> list[list[float]]:
    """ORS Directions (foot-walking, GeoJSON) — returns [[lon,lat], ...] polyline.

    Raises on any failure so the caller can fall back to straight lines.
    """
    if not settings.ors_api_key:
        raise RuntimeError("ORS_API_KEY not configured")
    r = httpx.post(
        f"{settings.ors_base_url}/v2/directions/foot-walking/geojson",
        headers={"Authorization": settings.ors_api_key, "Content-Type": "application/json", **UA},
        json={"coordinates": [lonlat_a, lonlat_b]},
        timeout=15,
    )
    r.raise_for_status()
    coords = r.json()["features"][0]["geometry"]["coordinates"]
    if not coords or len(coords) < 2:
        raise RuntimeError("ORS returned empty geometry")
    return coords


def ors_route_cached(db, from_id: int, to_id: int, from_lonlat: list[float],
                     to_lonlat: list[float]) -> list[list[float]]:
    """Cache-first polyline for one leg: check the `routes` table, then ORS.

    On a cache miss with a working key, the fetched geometry is persisted so
    subsequent calls never hit ORS again. Returns straight-line geometry when
    there's no key, ORS is down, or either point is missing — the map always
    gets something drawable.
    """
    from app.models import Route

    row = db.query(Route).filter_by(from_id=from_id, to_id=to_id).first()
    if row and row.geometry and len(row.geometry) >= 2:
        return row.geometry

    try:
        geom = ors_route(from_lonlat, to_lonlat)
    except Exception:
        return [from_lonlat, to_lonlat]  # straight-line fallback

    try:
        db.add(Route(from_id=from_id, to_id=to_id, geometry=geom))
        db.commit()
    except Exception:
        db.rollback()  # caching is best-effort; never fail the request over it
    return geom
