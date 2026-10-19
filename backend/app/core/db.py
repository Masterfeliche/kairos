"""SQLAlchemy engine / session factory."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def atomic(session: Session):
    """Run a block atomically, committing on success and rolling back on error.

    Unlike ``with session.begin()`` this is safe to use even if the caller's session
    already has an implicit transaction open (e.g. after a read), which is the norm
    inside request handlers and tests.
    """
    try:
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise
