import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.settings import get_settings


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    system_name: Mapped[str] = mapped_column(String(256))
    system_description: Mapped[str] = mapped_column(Text)
    owner_name: Mapped[str] = mapped_column(String(256))
    owner_email: Mapped[str] = mapped_column(String(256))
    area: Mapped[str] = mapped_column(String(128))
    organization: Mapped[str | None] = mapped_column(String(256), nullable=True)
    stack_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stack_resolved: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    root_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    dream_teams: Mapped[list["DreamTeam"]] = relationship(back_populates="project")


class DreamTeam(Base):
    __tablename__ = "dream_teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    slug: Mapped[str] = mapped_column(String(128), index=True)
    workflow: Mapped[str] = mapped_column(String(64))
    agents: Mapped[list[str]] = mapped_column(JSONB, default=list)
    models: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    matcher_source: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="ready")
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="dream_teams")
    tasks: Mapped[list["Task"]] = relationship(back_populates="dream_team")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    project_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True
    )
    dream_team_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dream_teams.id"), nullable=True, index=True
    )
    workflow: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    demand: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    steps: Mapped[list["TaskStep"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    project: Mapped["Project | None"] = relationship(back_populates="tasks")
    dream_team: Mapped["DreamTeam | None"] = relationship(back_populates="tasks")


class TaskStep(Base):
    __tablename__ = "task_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    model_provider: Mapped[str] = mapped_column(String(32))
    model_name: Mapped[str] = mapped_column(String(128))
    model_source: Mapped[str] = mapped_column(String(32))
    tokens_estimated: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["Task"] = relationship(back_populates="steps")


class CustomAgent(Base):
    __tablename__ = "custom_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(Text, default="")
    prompt_md: Mapped[str] = mapped_column(Text)
    default_provider: Mapped[str] = mapped_column(String(32))
    default_model: Mapped[str] = mapped_column(String(128))
    default_temperature: Mapped[float] = mapped_column(Float, default=0.2)
    tools: Mapped[list[str]] = mapped_column(JSONB, default=list)
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    restrictions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MemoryDocument(Base):
    __tablename__ = "memory_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(128), index=True)
    doc_type: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(get_settings().vector_dimension), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelUsageLog(Base):
    __tablename__ = "model_usage_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    agent: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(32))
    tokens_estimated: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    artifact_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
