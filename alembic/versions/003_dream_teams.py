"""add dream_teams table

Revision ID: 003
Revises: 002
Create Date: 2026-05-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _index_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in insp.get_table_names():
        if name in {idx["name"] for idx in insp.get_indexes(table)}:
            return True
    return False


def _fk_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in insp.get_table_names():
        if name in {fk["name"] for fk in insp.get_foreign_keys(table)}:
            return True
    return False


def upgrade() -> None:
    if not _table_exists("dream_teams"):
        op.create_table(
            "dream_teams",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("project_uuid", sa.UUID(), nullable=False),
            sa.Column("slug", sa.String(128), nullable=False),
            sa.Column("workflow", sa.String(64), nullable=False),
            sa.Column("agents", sa.dialects.postgresql.JSONB(), nullable=False),
            sa.Column("models", sa.dialects.postgresql.JSONB(), nullable=False),
            sa.Column("matcher_source", sa.String(32), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("user_id", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["project_uuid"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists("ix_dream_teams_slug"):
        op.create_index("ix_dream_teams_slug", "dream_teams", ["slug"])
    if not _index_exists("ix_dream_teams_project_uuid"):
        op.create_index("ix_dream_teams_project_uuid", "dream_teams", ["project_uuid"])

    if not _column_exists("tasks", "dream_team_uuid"):
        op.add_column("tasks", sa.Column("dream_team_uuid", sa.UUID(), nullable=True))
    if not _fk_exists("fk_tasks_dream_team_uuid"):
        op.create_foreign_key(
            "fk_tasks_dream_team_uuid",
            "tasks",
            "dream_teams",
            ["dream_team_uuid"],
            ["id"],
        )
    if not _index_exists("ix_tasks_dream_team_uuid"):
        op.create_index("ix_tasks_dream_team_uuid", "tasks", ["dream_team_uuid"])


def downgrade() -> None:
    if _index_exists("ix_tasks_dream_team_uuid"):
        op.drop_index("ix_tasks_dream_team_uuid", table_name="tasks")
    if _fk_exists("fk_tasks_dream_team_uuid"):
        op.drop_constraint("fk_tasks_dream_team_uuid", "tasks", type_="foreignkey")
    if _column_exists("tasks", "dream_team_uuid"):
        op.drop_column("tasks", "dream_team_uuid")
    if _index_exists("ix_dream_teams_project_uuid"):
        op.drop_index("ix_dream_teams_project_uuid", table_name="dream_teams")
    if _index_exists("ix_dream_teams_slug"):
        op.drop_index("ix_dream_teams_slug", table_name="dream_teams")
    if _table_exists("dream_teams"):
        op.drop_table("dream_teams")
