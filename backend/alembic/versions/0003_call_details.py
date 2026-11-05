"""Buyer role, recording egress and end reason on practice sessions.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("audience_type", "egress_id", "end_reason")


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column("practice_sessions", sa.Column(name, sa.String(), nullable=True))


def downgrade() -> None:
    for name in reversed(COLUMNS):
        op.drop_column("practice_sessions", name)
