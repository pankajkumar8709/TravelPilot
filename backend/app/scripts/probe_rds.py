"""Phase 0 probe — confirm SQLAlchemy can reach the target database.

Reads DATABASE_URL from env/.env. Prints the server version and a round-trip
SELECT so 'it works' is proven, not assumed. Run locally AND from an App Runner
shell against the RDS endpoint.

Usage:
  set DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/travelpilot
  python -m app.scripts.probe_rds
"""
from __future__ import annotations

from sqlalchemy import create_engine, text

from app.config import settings


def main() -> int:
    url = settings.database_url
    kind = "SQLite (local fallback)" if url.startswith("sqlite") else "Postgres/RDS"
    print(f"[probe_rds] DATABASE_URL kind: {kind}")
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            if url.startswith("sqlite"):
                v = conn.execute(text("select sqlite_version()")).scalar()
                print(f"[probe_rds] OK — SQLite version {v}")
            else:
                v = conn.execute(text("select version()")).scalar()
                print(f"[probe_rds] OK — {v}")
            rt = conn.execute(text("select 1")).scalar()
            assert rt == 1
        print("[probe_rds] round-trip SELECT 1 OK — SQLAlchemy connectivity confirmed.")
        return 0
    except Exception as e:
        print(f"[probe_rds] FAILED: {e}")
        print("  - check the RDS security group allows your IP / App Runner egress")
        print("  - check the endpoint host, port 5432, db name, and credentials")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
