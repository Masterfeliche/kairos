"""Copy every row from one database into another (e.g. local SQLite -> production Postgres).

The target must already have the current schema (``alembic upgrade head``) and be empty.
Tables are copied parent-first using the ORM metadata, so types (UUIDs, times, booleans,
enums) are converted by SQLAlchemy rather than by hand.
"""
from __future__ import annotations

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine

from app.models import Base

BATCH = 1000


def _connect_args(url: str) -> dict:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


def copy_database(source_url: str, target: Engine, *, log=print) -> dict[str, int]:
    source = create_engine(source_url, connect_args=_connect_args(source_url), future=True)
    tables = Base.metadata.sorted_tables
    counts: dict[str, int] = {}
    with source.connect() as src, target.begin() as dst:
        non_empty = [t.name for t in tables if dst.execute(select(func.count()).select_from(t)).scalar()]
        if non_empty:
            raise RuntimeError(
                "Target database is not empty (" + ", ".join(non_empty) + "). "
                "Copy into a freshly migrated database."
            )
        for table in tables:
            rows = src.execute(table.select()).mappings()
            total = 0
            while True:
                batch = rows.fetchmany(BATCH)
                if not batch:
                    break
                dst.execute(table.insert(), [dict(r) for r in batch])
                total += len(batch)
            counts[table.name] = total
            log(f"  {table.name}: {total}")
    source.dispose()
    return counts
