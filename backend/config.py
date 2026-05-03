"""
config.py
---------
Centralized settings loaded from .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ─── Supabase ────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    # ─── Gemini ──────────────────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ─── n8n ─────────────────────────────────────────────────
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""

    # ─── Agent Config ─────────────────────────────────────────
    MAX_REPAIR_ATTEMPTS: int = 3
    MAX_REFLECTION_ATTEMPTS: int = 2
    MAX_NODE_CANDIDATES: int = 5

    # ─── App ─────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
