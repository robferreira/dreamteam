"""add timeline column to tasks

Revision ID: 004
Revises: 003
Create Date: 2026-05-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _column_exists("tasks", "timeline"):
        op.add_column("tasks", sa.Column("timeline", sa.dialects.postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    if _column_exists("tasks", "timeline"):
        op.drop_column("tasks", "timeline")
