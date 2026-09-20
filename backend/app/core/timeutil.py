"""Time helpers — minutes-since-midnight <-> 'HH:MM', and OSM opening-hours check.

Plan Phase 3/5 note: OSM `opening_hours` is sparse/inconsistent. Decision here:
MISSING or unparseable hours => treat as OPEN (do not exclude), so thin OSM data
never silently empties the candidate set. A parseable simple range is respected.
"""
from __future__ import annotations

import re


def to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(minutes: int) -> str:
    minutes = max(0, min(24 * 60 - 1, int(round(minutes))))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


_RANGE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


def is_open_during(opening_hours: str, start_min: int, end_min: int) -> bool:
    """True if the place is open for the [start,end] window.

    Missing / '24/7' / unparseable -> assume open (documented fallback).
    Parses the first HH:MM-HH:MM range found (good enough for a demo dataset).
    """
    if not opening_hours or opening_hours.strip() in ("24/7", "24/7 open", ""):
        return True
    m = _RANGE.search(opening_hours)
    if not m:
        return True  # unparseable -> assume open
    o = int(m.group(1)) * 60 + int(m.group(2))
    c = int(m.group(3)) * 60 + int(m.group(4))
    if c <= o:  # overnight or malformed -> assume open
        return True
    return o <= start_min and end_min <= c
