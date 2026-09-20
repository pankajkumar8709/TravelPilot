"""Database engine + session (Phase 0: SQLAlchemy connects local + App Runner)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Postgres/RDS: fail fast (~10s) instead of hanging forever when the RDS
    # security group blocks the current IP or the host is unreachable.
    connect_args = {"connect_timeout": 10}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


# Additive, idempotent column migration: create_all() makes missing TABLES but
# never alters existing ones, so a schema evolution (e.g. the `city` slug used
# for multi-city generation) must be ALTERed onto long-lived databases like
# the RDS instance. Safe on SQLite and Postgres; runs on every boot.
_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, DDL type)
    ("places", "city", "VARCHAR(80) DEFAULT 'delhi'"),
    ("amenities", "city", "VARCHAR(80) DEFAULT 'delhi'"),
    ("trips", "city", "VARCHAR(80) DEFAULT 'delhi'"),
]


def _add_missing_columns() -> None:
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.connect() as conn:
        for table, column, ddl in _MIGRATIONS:
            if table not in insp.get_table_names():
                continue  # create_all() just made it fresh, columns included
            cols = {c["name"] for c in insp.get_columns(table)}
            if column not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        conn.commit()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
