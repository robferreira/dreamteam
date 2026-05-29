"""add projects table and task project_uuid

Revision ID: 002
Revises: 001
Create Date: 2026-05-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("system_name", sa.String(256), nullable=False),
        sa.Column("system_description", sa.Text(), nullable=False),
        sa.Column("owner_name", sa.String(256), nullable=False),
        sa.Column("owner_email", sa.String(256), nullable=False),
        sa.Column("area", sa.String(128), nullable=False),
        sa.Column("organization", sa.String(256), nullable=True),
        sa.Column("stack_hint", sa.String(64), nullable=True),
        sa.Column("stack_resolved", sa.String(64), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("root_path", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])

    op.add_column("tasks", sa.Column("project_uuid", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_project_uuid",
        "tasks",
        "projects",
        ["project_uuid"],
        ["id"],
    )
    op.create_index("ix_tasks_project_uuid", "tasks", ["project_uuid"])


def downgrade() -> None:
    op.drop_index("ix_tasks_project_uuid", table_name="tasks")
    op.drop_constraint("fk_tasks_project_uuid", "tasks", type_="foreignkey")
    op.drop_column("tasks", "project_uuid")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")
