"""date-scope class-rep changes: per-week session occurrences

Class-rep live status and reschedules used to be written onto the weekly template row,
so a class marked "not held" on Monday stayed "not held" every Monday and one-off moves
became permanent. They now live in ``session_occurrence`` (one row per session per
teaching week) and venue heads-ups carry the week they apply to.

Data: template rows that had been moved are restored to their published slot (the
change cannot be tied to a date); a non-default live status becomes an occurrence in
the week it was set. Active venue notices are assigned the week they were created.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-19 12:00:00.000000
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LIVE_STATUS = sa.Enum("scheduled", "live", "ended", "not_held", name="live_status", native_enum=False)
EAT = timezone(timedelta(hours=3))

_session = sa.table(
    "timetable_session",
    sa.column("id", sa.Uuid()),
    sa.column("day_of_week", sa.SmallInteger()),
    sa.column("start_time", sa.Time()),
    sa.column("end_time", sa.Time()),
    sa.column("venue_id", sa.Uuid()),
    sa.column("venue_raw", sa.Text()),
    sa.column("updated_at", sa.DateTime(timezone=True)),
    sa.column("live_status", sa.String()),
    sa.column("live_started_at", sa.DateTime(timezone=True)),
    sa.column("live_ended_at", sa.DateTime(timezone=True)),
    sa.column("rescheduled_at", sa.DateTime(timezone=True)),
    sa.column("original_day_of_week", sa.SmallInteger()),
    sa.column("original_start_time", sa.Time()),
    sa.column("original_end_time", sa.Time()),
    sa.column("original_venue_raw", sa.Text()),
)
_occurrence = sa.table(
    "session_occurrence",
    sa.column("id", sa.Uuid()),
    sa.column("session_id", sa.Uuid()),
    sa.column("week_start", sa.Date()),
    sa.column("live_status", sa.String()),
    sa.column("live_started_at", sa.DateTime(timezone=True)),
    sa.column("live_ended_at", sa.DateTime(timezone=True)),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
_venue = sa.table("venue", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
_notice = sa.table(
    "venue_notice",
    sa.column("id", sa.Uuid()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("week_start", sa.Date()),
)


def _monday(at: datetime | None) -> date:
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    d = at.astimezone(EAT).date()
    return d - timedelta(days=d.weekday())


def upgrade() -> None:
    op.create_table(
        "session_occurrence",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("live_status", LIVE_STATUS, nullable=False, server_default="scheduled"),
        sa.Column("live_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moved_day_of_week", sa.SmallInteger(), nullable=True),
        sa.Column("moved_start_time", sa.Time(), nullable=True),
        sa.Column("moved_end_time", sa.Time(), nullable=True),
        sa.Column("moved_venue_raw", sa.Text(), nullable=True),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["timetable_session.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "week_start", name="uq_occurrence_week"),
    )
    op.create_index("ix_session_occurrence_session_id", "session_occurrence", ["session_id"])
    op.create_index("ix_session_occurrence_week_start", "session_occurrence", ["week_start"])

    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    venue_ids = {code: vid for vid, code in bind.execute(sa.select(_venue.c.id, _venue.c.code))}

    for row in bind.execute(sa.select(_session).where(
        sa.or_(_session.c.rescheduled_at.is_not(None), _session.c.live_status != "scheduled")
    )).mappings().all():
        if row["live_status"] and row["live_status"] != "scheduled":
            bind.execute(_occurrence.insert().values(
                id=uuid.uuid4(), session_id=row["id"],
                week_start=_monday(row["live_ended_at"] or row["live_started_at"] or row["updated_at"]),
                live_status=row["live_status"], live_started_at=row["live_started_at"],
                live_ended_at=row["live_ended_at"], created_at=now, updated_at=now,
            ))
        if row["rescheduled_at"] is not None and row["original_start_time"] is not None:
            venue = row["original_venue_raw"]
            bind.execute(_session.update().where(_session.c.id == row["id"]).values(
                day_of_week=row["original_day_of_week"] or row["day_of_week"],
                start_time=row["original_start_time"],
                end_time=row["original_end_time"] or row["end_time"],
                venue_raw=venue,
                venue_id=venue_ids.get(venue) if venue else None,
            ))

    with op.batch_alter_table("timetable_session") as batch:
        for col in ("original_venue_raw", "original_end_time", "original_start_time",
                    "original_day_of_week", "reschedule_reason", "rescheduled_at",
                    "live_ended_at", "live_started_at", "live_status"):
            batch.drop_column(col)

    with op.batch_alter_table("venue_notice") as batch:
        batch.add_column(sa.Column("week_start", sa.Date(), nullable=True))
    for nid, created in bind.execute(sa.select(_notice.c.id, _notice.c.created_at)).all():
        bind.execute(_notice.update().where(_notice.c.id == nid).values(week_start=_monday(created)))
    with op.batch_alter_table("venue_notice") as batch:
        batch.alter_column("week_start", existing_type=sa.Date(), nullable=False)
        batch.create_index("ix_venue_notice_week_start", ["week_start"])


def downgrade() -> None:
    with op.batch_alter_table("venue_notice") as batch:
        batch.drop_index("ix_venue_notice_week_start")
        batch.drop_column("week_start")
    with op.batch_alter_table("timetable_session") as batch:
        batch.add_column(sa.Column("live_status", LIVE_STATUS, nullable=False,
                                   server_default="scheduled"))
        batch.add_column(sa.Column("live_started_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("live_ended_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("rescheduled_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("reschedule_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("original_day_of_week", sa.SmallInteger(), nullable=True))
        batch.add_column(sa.Column("original_start_time", sa.Time(), nullable=True))
        batch.add_column(sa.Column("original_end_time", sa.Time(), nullable=True))
        batch.add_column(sa.Column("original_venue_raw", sa.Text(), nullable=True))
    op.drop_index("ix_session_occurrence_week_start", table_name="session_occurrence")
    op.drop_index("ix_session_occurrence_session_id", table_name="session_occurrence")
    op.drop_table("session_occurrence")
