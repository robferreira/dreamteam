"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.String(128), nullable=False),
        sa.Column("workflow", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("demand", sa.Text(), nullable=False),
        sa.Column("result", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("thread_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_thread_id", "tasks", ["thread_id"])

    op.create_table(
        "task_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("model_provider", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_source", sa.String(32), nullable=False),
        sa.Column("tokens_estimated", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("output", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_steps_task_id", "task_steps", ["task_id"])

    op.create_table(
        "custom_agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("prompt_md", sa.Text(), nullable=False),
        sa.Column("default_provider", sa.String(32), nullable=False),
        sa.Column("default_model", sa.String(128), nullable=False),
        sa.Column("default_temperature", sa.Float(), nullable=False),
        sa.Column("tools", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("permissions", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("restrictions", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("context", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=True),
        sa.Column("visibility", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_custom_agents_slug", "custom_agents", ["slug"])

    op.create_table(
        "memory_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.String(128), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_documents_project_id", "memory_documents", ["project_id"])
    op.create_index("ix_memory_documents_doc_type", "memory_documents", ["doc_type"])

    op.create_table(
        "model_usage_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("tokens_estimated", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_tier", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("content", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_task_id", "artifacts", ["task_id"])


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("model_usage_log")
    op.drop_table("memory_documents")
    op.drop_table("custom_agents")
    op.drop_table("task_steps")
    op.drop_table("tasks")
