"""class representatives, live status, reschedule

Revision ID: b2c3d4e5f6a7
Revises: a1f2c3d4e5b6
Create Date: 2026-10-15 13:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1f2c3d4e5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LIVE_STATUS = sa.Enum("scheduled", "live", "ended", "not_held", name="live_status", native_enum=False)


def upgrade() -> None:
    # Class-representative accounts reuse admin_user with role='cr'; the enum is a
    # VARCHAR (native_enum=False) so no type change is required.
    with op.batch_alter_table("admin_user") as batch:
        batch.add_column(sa.Column("display_name", sa.Text(), nullable=True))

    op.create_table(
        "cohort_representative",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], ["cohort.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "cohort_id"),
    )

    with op.batch_alter_table("timetable_session") as batch:
        batch.add_column(sa.Column("live_status", LIVE_STATUS, nullable=False,
                                   server_default="scheduled"))
        batch.add_column(sa.Column("live_started_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("live_ended_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("rescheduled_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("reschedule_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("original_start_time", sa.Time(), nullable=True))
        batch.add_column(sa.Column("original_end_time", sa.Time(), nullable=True))
        batch.add_column(sa.Column("original_venue_raw", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("timetable_session") as batch:
        batch.drop_column("original_venue_raw")
        batch.drop_column("original_end_time")
        batch.drop_column("original_start_time")
        batch.drop_column("reschedule_reason")
        batch.drop_column("rescheduled_at")
        batch.drop_column("live_ended_at")
        batch.drop_column("live_started_at")
        batch.drop_column("live_status")
    op.drop_table("cohort_representative")
    with op.batch_alter_table("admin_user") as batch:
        batch.drop_column("display_name")
