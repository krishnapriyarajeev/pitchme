"""Voice clone status and error on users.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

voice_clone_status = postgresql.ENUM(
    "pending", "ready", "failed", name="voice_clone_status", create_type=False
)


def upgrade() -> None:
    voice_clone_status.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("voice_clone_status", voice_clone_status, nullable=True))
    op.add_column("users", sa.Column("voice_clone_error", sa.String(), nullable=True))
    # Users who already have a clone keep it as ready.
    op.execute("UPDATE users SET voice_clone_status = 'ready' WHERE voice_clone_id IS NOT NULL")


def downgrade() -> None:
    op.drop_column("users", "voice_clone_error")
    op.drop_column("users", "voice_clone_status")
    voice_clone_status.drop(op.get_bind(), checkfirst=True)
