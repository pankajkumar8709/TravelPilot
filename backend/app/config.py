"""Application configuration.

Phase 0 (Stack + Strategy Lock): secrets/config strategy.
- DATABASE_URL: RDS Postgres in prod (App Runner env var), SQLite fallback for local dev
  so SQLAlchemy connects identically in both places (plan Phase 0 exit criteria).
- Bedrock: model id + region, used ONLY for interest/category prioritization (plan Phase 4/8).
- External reference APIs (Overpass/Nominatim/ORS) are used at INGESTION time only,
  never at runtime (plan Phase 3 data-sourcing principle).
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database (Phase 0 / Phase 3) ---
    # Prod: postgresql+psycopg2://user:pass@host:5432/travelpilot  (RDS)
    # Local fallback: sqlite file in the backend dir.
    database_url: str = "sqlite:///./travelpilot.db"

    # --- LLM provider: Groq (OpenAI-compatible). The LLM is interface, not authority. ---
    # Bedrock was unavailable on this AWS account, so the AI layer runs on Groq.
    use_mock_llm: bool = True  # flip to False once GROQ_API_KEY is set
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com"
    # (legacy Bedrock knobs kept for the deploy templates; unused by llm.py now)
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    aws_region_name: str = "us-east-1"
    aws_profile: str = ""

    # --- External reference-data APIs (Phase 3 ingestion ONLY) ---
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    ors_base_url: str = "https://api.openrouteservice.org"
    ors_api_key: str = ""  # set for ingestion; never called at runtime

    # --- Phase 10 S3 data lake (raw ingest responses land here before RDS) ---
    data_lake_bucket: str = ""

    # Auto-seed a fresh DB on first boot so the deployed app renders immediately.
    auto_seed: bool = True

    # --- Currency (Phase 6) ---
    frankfurter_url: str = "https://api.frankfurter.app"

    # --- CORS (frontend origin) ---
    cors_origins: str = "*"


settings = Settings()
