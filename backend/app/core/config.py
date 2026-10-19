"""Application configuration (env-driven, safe defaults for local dev)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TT_", env_file=".env", extra="ignore")

    # Local dev defaults to SQLite so the pipeline runs with zero setup.
    # Production sets TT_DATABASE_URL to a Postgres DSN.
    database_url: str = "sqlite+pysqlite:///./smarttimetable.db"

    # Where immutable source PDFs and rendered page images live.
    storage_dir: Path = Path("./data/storage")

    # Import limits (see docs/05-system-architecture.md §6.7).
    max_upload_bytes: int = 50 * 1024 * 1024
    max_pages: int = 1000

    # Cookies: set True in production (HTTPS).
    secure_cookies: bool = False

    # Browser origin allowed to call the admin API (Next.js dev server).
    frontend_origin: str = "http://localhost:3000"

    # DEV/STAGING ONLY: let the public API serve the latest unpublished (review) version
    # so the student site can be previewed before a version passes the publish gate.
    # MUST remain False in production.
    allow_draft_preview: bool = False

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
