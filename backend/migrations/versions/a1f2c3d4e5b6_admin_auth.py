"""admin auth: admin_user, admin_session, audit actor

Revision ID: a1f2c3d4e5b6
Revises: d4ee37b27f55
Create Date: 2026-10-15 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1f2c3d4e5b6"
down_revision: Union[str, None] = "d4ee37b27f55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_ROLE = sa.Enum("admin", "reviewer", "owner", name="admin_role", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "admin_user",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", ADMIN_ROLE, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "admin_session",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_admin_session_user_id", "admin_session", ["user_id"])
    op.create_index("ix_admin_session_token_hash", "admin_session", ["token_hash"])

    with op.batch_alter_table("audit_event") as batch:
        batch.add_column(sa.Column("actor_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_audit_actor", "admin_user", ["actor_id"], ["id"])
    op.create_index("ix_audit_event_actor_id", "audit_event", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_event_actor_id", table_name="audit_event")
    with op.batch_alter_table("audit_event") as batch:
        batch.drop_constraint("fk_audit_actor", type_="foreignkey")
        batch.drop_column("actor_id")
    op.drop_index("ix_admin_session_token_hash", table_name="admin_session")
    op.drop_index("ix_admin_session_user_id", table_name="admin_session")
    op.drop_table("admin_session")
    op.drop_table("admin_user")
