"""Wikimedia Commons image lookup (keyless) — real place photos.

Given a place name, query the Wikipedia REST summary API for a representative
image (thumbnail). No API key required. Returns "" on any failure so callers
degrade to a gradient placeholder in the UI.
"""
from __future__ import annotations

import httpx

UA = {"User-Agent": "TravelPilot/1.0 (hackathon; travelpilot@example.com)"}


def image_for(place_name: str) -> str:
    """Best-effort thumbnail URL for a place. Empty string if none found."""
    # Strip parentheticals/qualifiers that hurt the title match, e.g. "Red Fort (Lal Qila)".
    title = place_name.split("(")[0].strip()
    try:
        from urllib.parse import quote

        r = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}",
            headers=UA, timeout=10, follow_redirects=True,
        )
        if r.status_code != 200:
            return ""
        data = r.json()
        # prefer the original image, fall back to the thumbnail
        return (data.get("originalimage") or {}).get("source") \
            or (data.get("thumbnail") or {}).get("source") or ""
    except Exception:
        return ""
