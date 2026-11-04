"""Initial schema: users and practice sessions.

Revision ID: 0001
Revises:
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

session_status = postgresql.ENUM(
    "waiting", "active", "complete", "failed", name="session_status", create_type=False
)
analysis_status = postgresql.ENUM(
    "not_started",
    "queued",
    "running",
    "complete",
    "failed",
    name="analysis_status",
    create_type=False,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    session_status.create(op.get_bind(), checkfirst=True)
    analysis_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("role_title", sa.String(), nullable=True),
        sa.Column("sells", sa.String(), nullable=True),
        sa.Column("voice_sample_key", sa.String(), nullable=True),
        sa.Column("voice_transcript", sa.String(), nullable=True),
        sa.Column("voice_clone_id", sa.String(), nullable=True),
        sa.Column("playbook_key", sa.String(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("room_name", sa.String(), nullable=False),
        sa.Column("status", session_status, nullable=False),
        sa.Column("prospect_name", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("deal_stage", sa.String(), nullable=False),
        sa.Column("buyer_composure", sa.String(), nullable=True),
        sa.Column("competitors", sa.String(), nullable=True),
        sa.Column("transcript", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recording_key", sa.String(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_status", analysis_status, nullable=False),
        sa.Column("analysis_stage", sa.String(), nullable=True),
        sa.Column("analysis_error", sa.String(), nullable=True),
        sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_practice_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_sessions")),
    )
    op.create_index(
        op.f("ix_practice_sessions_user_id"), "practice_sessions", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_practice_sessions_user_id"), table_name="practice_sessions")
    op.drop_table("practice_sessions")
    op.drop_table("users")
    analysis_status.drop(op.get_bind(), checkfirst=True)
    session_status.drop(op.get_bind(), checkfirst=True)
