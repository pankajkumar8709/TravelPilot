"""SQLAlchemy models — the finalized Postgres schema from plan Phase 3,
plus Phase 4 `suggestions` and Phase 7 pending-change (`itinerary_changes`).

Tables (plan Phase 3 verbatim):
  places        (id, name, coords, category, opening_hours)
  amenities     (id, name, coords, type)            # toilets/ATM/pharmacy — map overlay only
  travel_times  (from_id, to_id, duration_minutes, mode)
  routes        (from_id, to_id, geometry)          # polyline for map rendering
  trips, days, activities, bookings

Phase 4:  suggestions (day_id, type, time_window, place_id, rank)  # offered, never scheduled
Phase 7:  itinerary_changes (pending diff, applied only on user confirm)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Reference data (Phase 3) — ingested once, read-only at runtime
# ---------------------------------------------------------------------------
class Place(Base):
    __tablename__ = "places"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    city: Mapped[str] = mapped_column(String(80), default="delhi", index=True)  # city slug
    category: Mapped[str] = mapped_column(String(50))  # food/culture/outdoor/... or "hotel"
    interest_tag: Mapped[str] = mapped_column(String(50), default="")
    opening_hours: Mapped[str] = mapped_column(String(200), default="")  # OSM opening_hours string
    avg_visit_minutes: Mapped[int] = mapped_column(Integer, default=60)
    cost: Mapped[float] = mapped_column(Float, default=0.0)  # est. per-person cost (Phase 6)
    website: Mapped[str] = mapped_column(String(300), default="")  # Phase 4 "view & book"
    image_url: Mapped[str] = mapped_column(String(500), default="")  # real place photo (Wikimedia)


class Amenity(Base):
    __tablename__ = "amenities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    city: Mapped[str] = mapped_column(String(80), default="delhi", index=True)  # city slug
    type: Mapped[str] = mapped_column(String(30))  # toilets / atm / pharmacy


class TravelTime(Base):
    __tablename__ = "travel_times"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_id: Mapped[int] = mapped_column(Integer, index=True)
    to_id: Mapped[int] = mapped_column(Integer, index=True)
    duration_minutes: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(20), default="foot-walking")


class Route(Base):
    __tablename__ = "routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_id: Mapped[int] = mapped_column(Integer, index=True)
    to_id: Mapped[int] = mapped_column(Integer, index=True)
    geometry: Mapped[list] = mapped_column(JSON, default=list)  # [[lon,lat],...] polyline


# ---------------------------------------------------------------------------
# Trip state (Phase 2 core, evolved in Phase 3)
# ---------------------------------------------------------------------------
class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[str] = mapped_column(String(20))
    end_date: Mapped[str] = mapped_column(String(20))
    budget_total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    interests: Mapped[list] = mapped_column(JSON, default=list)  # ["food","culture",...]
    hotel_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_time_day1: Mapped[str] = mapped_column(String(8), default="09:00")
    pace: Mapped[str] = mapped_column(String(20), default="balanced")
    group_size: Mapped[int] = mapped_column(Integer, default=1)
    city: Mapped[str] = mapped_column(String(80), default="delhi")  # resolved city slug
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    days: Mapped[list["Day"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class Day(Base):
    __tablename__ = "days"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    date: Mapped[str] = mapped_column(String(20))
    day_index: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(8), default="09:00")
    end_time: Mapped[str] = mapped_column(String(8), default="21:00")

    trip: Mapped["Trip"] = relationship(back_populates="days")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id"))
    place_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    start_time: Mapped[str] = mapped_column(String(8))  # "HH:MM"
    end_time: Mapped[str] = mapped_column(String(8))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    interest_tag: Mapped[str] = mapped_column(String(50), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)  # order within the day
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lon: Mapped[float] = mapped_column(Float, default=0.0)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    # Phase 7: 1-2 precomputed backup alternates (list of place_ids)
    backups: Mapped[list] = mapped_column(JSON, default=list)

    day: Mapped["Day"] = relationship(back_populates="activities")


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    kind: Mapped[str] = mapped_column(String(30))  # flight / hotel / other
    reference: Mapped[str] = mapped_column(String(80), default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="confirmed")


# ---------------------------------------------------------------------------
# Phase 4 — suggestions (offered, never scheduled)
# ---------------------------------------------------------------------------
class Suggestion(Base):
    __tablename__ = "suggestions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id"))
    type: Mapped[str] = mapped_column(String(20))  # food / stay
    time_window: Mapped[str] = mapped_column(String(40))  # "dinner ~8-10pm"
    place_id: Mapped[int] = mapped_column(Integer)
    place_name: Mapped[str] = mapped_column(String(200), default="")
    rank: Mapped[int] = mapped_column(Integer, default=1)
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lon: Mapped[float] = mapped_column(Float, default=0.0)
    website: Mapped[str] = mapped_column(String(300), default="")

    day: Mapped["Day"] = relationship(back_populates="suggestions")


# ---------------------------------------------------------------------------
# Phase 7 — pending disruption change (applied only on user confirm)
# ---------------------------------------------------------------------------
class ItineraryChange(Base):
    __tablename__ = "itinerary_changes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/applied/rejected
    reason: Mapped[str] = mapped_column(Text, default="")
    trigger: Mapped[str] = mapped_column(String(40), default="manual")  # manual/weather/flight
    diff: Mapped[dict] = mapped_column(JSON, default=dict)  # {added, removed, modified, stability}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
