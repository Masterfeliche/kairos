"""session move across days (original_day_of_week)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-15 15:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("timetable_session") as batch:
        batch.add_column(sa.Column("original_day_of_week", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("timetable_session") as batch:
        batch.drop_column("original_day_of_week")
