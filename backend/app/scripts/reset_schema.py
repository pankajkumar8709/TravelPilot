"""Reset the database schema to match the current models.

Base.metadata.create_all() only CREATES missing tables — it does NOT add new
columns to tables that already exist. When the models gain a column (e.g.
places.image_url, trips.start_time_day1) but the DB predates it, you get
'UndefinedColumn'. This script DROPS all tables and recreates them from the
current models. Demo data only — it destroys existing rows, then you re-seed.

Usage (DESTRUCTIVE — recreates the schema):
  python -m app.scripts.reset_schema
"""
from __future__ import annotations

from app.db import engine
from app.models import Base


def main() -> None:
    print("[reset_schema] dropping all tables…")
    Base.metadata.drop_all(bind=engine)
    print("[reset_schema] recreating tables from current models…")
    Base.metadata.create_all(bind=engine)
    print("[reset_schema] done. Now run: python -m app.scripts.seed && python -m app.scripts.seed_demo_trip")


if __name__ == "__main__":
    main()
