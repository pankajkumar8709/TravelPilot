"""Database engine + session (Phase 0: SQLAlchemy connects local + App Runner)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url
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
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        # Fail with a short, actionable message instead of the raw SQLAlchemy
        # traceback — a blocked RDS security group looks identical to a typo'd host.
        raise RuntimeError(_unreachable_message()) from e
    _add_missing_columns()


def _unreachable_message() -> str:
    url = make_url(settings.database_url)
    host = url.host or "?"
    port = url.port or 5432
    return (
        f"Cannot reach the database at {host}:{port}. "
        "If this is the RDS host from a laptop, check in the AWS console: "
        "(1) the instance is Publicly accessible = Yes, "
        "(2) its security group allows inbound TCP 5432 from your current IP "
        "(your IP changes often — re-check it), and "
        "(3) no VPN/corporate firewall is blocking outbound 5432. "
        "For local development you can instead clear DATABASE_URL in backend/.env "
        "to use the SQLite fallback."
    )


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
