"""add current_agent column to tasks

Revision ID: 005
Revises: 004
Create Date: 2026-05-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _column_exists("tasks", "current_agent"):
        op.add_column("tasks", sa.Column("current_agent", sa.String(64), nullable=True))


def downgrade() -> None:
    if _column_exists("tasks", "current_agent"):
        op.drop_column("tasks", "current_agent")
