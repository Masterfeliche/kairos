"""Test configuration: isolated SQLite DB + temp storage, set before app import."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.gettempdir())
_DB = _TMP / f"tt_test_{os.getpid()}.db"
_STORE = _TMP / f"tt_store_{os.getpid()}"

# Set TT_TEST_DATABASE_URL to run the suite against Postgres (it drops and recreates
# every table, so point it at a throwaway database).
os.environ["TT_DATABASE_URL"] = os.environ.get(
    "TT_TEST_DATABASE_URL", f"sqlite+pysqlite:///{_DB.as_posix()}"
)
os.environ["TT_STORAGE_DIR"] = str(_STORE)

import pytest  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PDF = PROJECT_ROOT / "TEACHING TIMETABLE 2026-2025 - SEMESTER I - Students.pdf"


@pytest.fixture(scope="session")
def pdf_path() -> Path:
    if not SOURCE_PDF.exists():
        pytest.skip(f"source PDF not found: {SOURCE_PDF}")
    return SOURCE_PDF

