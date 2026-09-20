"""API request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class TripCreate(BaseModel):
    destination: str = "Delhi"
    start_date: str
    end_date: str
    budget_total: float = 0.0
    currency: str = "INR"
    interests: list[str] = []
    hotel_place_id: int | None = None
    start_time_day1: str = "09:00"   # journey start on day 1 (drives meal/stay windows)
    pace: str = "balanced"           # relaxed | balanced | packed
    group_size: int = 1


class ChatAdd(BaseModel):
    trip_id: int
    place_query: str                 # free text, e.g. "IIT Delhi"
    day_index: int | None = None     # preferred day; None = auto-pick
    lang: str = "en"


class ChatMove(BaseModel):
    trip_id: int
    place_id: int
    to_day_index: int
    lang: str = "en"


class ChatReorder(BaseModel):
    trip_id: int
    day_index: int
    ordered_place_ids: list[int]


class ChatMessage(BaseModel):
    trip_id: int
    message: str
    lang: str = "en"


class DisruptionInject(BaseModel):
    trip_id: int
    day_index: int
    disrupted_place_id: int
    trigger: str = "manual"  # manual | weather | flight
    reason: str = ""


class NLQuery(BaseModel):
    trip_id: int
    question: str
    lang: str = "en"  # answer language hint (en/hi/ta/bn); multilingual NL support
