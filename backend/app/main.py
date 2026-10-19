"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, admin_auth, cr, public
from app.core.config import settings
from app.core.db import engine
from app.models import Base


def create_app() -> FastAPI:
    app = FastAPI(title="DIT Smart Timetable API", version="0.4.0")

    # Local SQLite convenience: create tables if migrations have not been run.
    # Postgres (production) is managed only by Alembic — creating tables here would
    # make `alembic upgrade head` fail on a fresh database.
    if settings.is_sqlite:
        Base.metadata.create_all(engine)

    # The Next.js dev server also proxies /api to this app (same-origin cookies);
    # CORS is a fallback for direct cross-origin calls.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(public.router)
    app.include_router(admin_auth.router)
    app.include_router(admin.router)
    app.include_router(cr.router)

    @app.get("/healthz", tags=["ops"])
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()
