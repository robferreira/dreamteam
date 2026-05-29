from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.memory.db_models import (
    Artifact,
    Base,
    CustomAgent,
    DreamTeam,
    MemoryDocument,
    ModelUsageLog,
    Project,
    Task,
    TaskStep,
)
from src.settings import get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_settings().database_url,
            echo=get_settings().app_env == "development",
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    from sqlalchemy import text

    engine = get_engine()
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
        await conn.run_sync(Base.metadata.create_all)


class TaskRepository:
    async def create_task(
        self,
        workflow: str,
        demand: str,
        project_id: str = "default",
        user_id: str | None = None,
        thread_id: str | None = None,
        project_uuid: UUID | None = None,
        dream_team_uuid: UUID | None = None,
    ) -> Task:
        async with get_session() as session:
            task = Task(
                workflow=workflow,
                demand=demand,
                project_id=project_id,
                project_uuid=project_uuid,
                dream_team_uuid=dream_team_uuid,
                user_id=user_id,
                thread_id=thread_id,
                status="running",
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            return task

    async def get_task(self, task_id: UUID) -> Task | None:
        async with get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_task_with_steps(self, task_id: UUID) -> Task | None:
        async with get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                await session.refresh(task, ["steps"])
            return task

    async def update_task(
        self,
        task_id: UUID,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        thread_id: str | None = None,
    ) -> None:
        async with get_session() as session:
            result_q = await session.execute(select(Task).where(Task.id == task_id))
            task = result_q.scalar_one_or_none()
            if not task:
                return
            if status is not None:
                task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if thread_id is not None:
                task.thread_id = thread_id

    async def add_step(
        self,
        task_id: UUID,
        agent: str,
        model_provider: str,
        model_name: str,
        model_source: str,
        tokens_estimated: int,
        latency_ms: int,
        output: dict[str, Any] | None = None,
    ) -> TaskStep:
        async with get_session() as session:
            step = TaskStep(
                task_id=task_id,
                agent=agent,
                model_provider=model_provider,
                model_name=model_name,
                model_source=model_source,
                tokens_estimated=tokens_estimated,
                latency_ms=latency_ms,
                output=output,
            )
            session.add(step)
            await session.flush()
            await session.refresh(step)
            return step

    async def log_model_usage(
        self,
        agent: str,
        provider: str,
        model: str,
        source: str,
        tokens_estimated: int,
        latency_ms: int,
        task_id: UUID | None = None,
        cost_tier: str | None = None,
    ) -> None:
        async with get_session() as session:
            session.add(
                ModelUsageLog(
                    task_id=task_id,
                    agent=agent,
                    provider=provider,
                    model=model,
                    source=source,
                    tokens_estimated=tokens_estimated,
                    latency_ms=latency_ms,
                    cost_tier=cost_tier,
                )
            )

    async def save_artifact(
        self,
        task_id: UUID,
        agent: str,
        artifact_type: str,
        content: dict[str, Any],
    ) -> None:
        async with get_session() as session:
            session.add(
                Artifact(
                    task_id=task_id,
                    agent=agent,
                    artifact_type=artifact_type,
                    content=content,
                )
            )


class ProjectRepository:
    async def create(self, data: dict[str, Any]) -> Project:
        async with get_session() as session:
            project = Project(**data)
            session.add(project)
            await session.flush()
            await session.refresh(project)
            return project

    async def get_by_slug(self, slug: str) -> Project | None:
        async with get_session() as session:
            result = await session.execute(select(Project).where(Project.slug == slug))
            return result.scalar_one_or_none()

    async def get_by_id(self, project_id: UUID) -> Project | None:
        async with get_session() as session:
            result = await session.execute(select(Project).where(Project.id == project_id))
            return result.scalar_one_or_none()

    async def update(self, slug: str, updates: dict[str, Any]) -> Project | None:
        async with get_session() as session:
            result = await session.execute(select(Project).where(Project.slug == slug))
            project = result.scalar_one_or_none()
            if not project:
                return None
            for key, value in updates.items():
                if hasattr(project, key) and value is not None:
                    setattr(project, key, value)
            await session.flush()
            await session.refresh(project)
            return project


class DreamTeamRepository:
    async def create(self, data: dict[str, Any]) -> DreamTeam:
        async with get_session() as session:
            team = DreamTeam(**data)
            session.add(team)
            await session.flush()
            await session.refresh(team)
            return team

    async def get_by_id(self, team_id: UUID) -> DreamTeam | None:
        async with get_session() as session:
            result = await session.execute(select(DreamTeam).where(DreamTeam.id == team_id))
            return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> DreamTeam | None:
        async with get_session() as session:
            result = await session.execute(
                select(DreamTeam).where(DreamTeam.slug == slug).order_by(DreamTeam.created_at.desc())
            )
            return result.scalars().first()

    async def get_by_project(self, project_uuid: UUID) -> DreamTeam | None:
        async with get_session() as session:
            result = await session.execute(
                select(DreamTeam)
                .where(DreamTeam.project_uuid == project_uuid)
                .order_by(DreamTeam.created_at.desc())
            )
            return result.scalars().first()

    async def update(self, team_id: UUID, updates: dict[str, Any]) -> DreamTeam | None:
        async with get_session() as session:
            result = await session.execute(select(DreamTeam).where(DreamTeam.id == team_id))
            team = result.scalar_one_or_none()
            if not team:
                return None
            for key, value in updates.items():
                if hasattr(team, key) and value is not None:
                    setattr(team, key, value)
            await session.flush()
            await session.refresh(team)
            return team


class CustomAgentRepository:
    async def create(self, data: dict[str, Any]) -> CustomAgent:
        async with get_session() as session:
            agent = CustomAgent(**data)
            session.add(agent)
            await session.flush()
            await session.refresh(agent)
            return agent

    async def get_by_slug(self, slug: str) -> CustomAgent | None:
        async with get_session() as session:
            result = await session.execute(
                select(CustomAgent).where(CustomAgent.slug == slug)
            )
            return result.scalar_one_or_none()

    async def get_by_id(self, agent_id: UUID) -> CustomAgent | None:
        async with get_session() as session:
            result = await session.execute(
                select(CustomAgent).where(CustomAgent.id == agent_id)
            )
            return result.scalar_one_or_none()

    async def update(self, agent_id: UUID, updates: dict[str, Any]) -> CustomAgent | None:
        async with get_session() as session:
            result = await session.execute(
                select(CustomAgent).where(CustomAgent.id == agent_id)
            )
            agent = result.scalar_one_or_none()
            if not agent:
                return None
            for key, value in updates.items():
                if hasattr(agent, key) and value is not None:
                    setattr(agent, key, value)
            await session.flush()
            await session.refresh(agent)
            return agent


class MemoryDocumentRepository:
    async def add_document(
        self,
        project_id: str,
        doc_type: str,
        content: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryDocument:
        async with get_session() as session:
            doc = MemoryDocument(
                project_id=project_id,
                doc_type=doc_type,
                content=content,
                embedding=embedding,
                metadata_=metadata or {},
            )
            session.add(doc)
            await session.flush()
            await session.refresh(doc)
            return doc

    async def search_similar(
        self,
        embedding: list[float],
        project_id: str,
        limit: int = 5,
        doc_types: list[str] | None = None,
    ) -> list[MemoryDocument]:
        async with get_session() as session:
            query = (
                select(MemoryDocument)
                .where(MemoryDocument.project_id == project_id)
                .where(MemoryDocument.embedding.isnot(None))
                .order_by(MemoryDocument.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            if doc_types:
                query = query.where(MemoryDocument.doc_type.in_(doc_types))
            result = await session.execute(query)
            return list(result.scalars().all())


_task_repo: TaskRepository | None = None
_project_repo: ProjectRepository | None = None
_dream_team_repo: DreamTeamRepository | None = None
_custom_agent_repo: CustomAgentRepository | None = None
_memory_doc_repo: MemoryDocumentRepository | None = None


def get_task_repository() -> TaskRepository:
    global _task_repo
    if _task_repo is None:
        _task_repo = TaskRepository()
    return _task_repo


def get_project_repository() -> ProjectRepository:
    global _project_repo
    if _project_repo is None:
        _project_repo = ProjectRepository()
    return _project_repo


def get_dream_team_repository() -> DreamTeamRepository:
    global _dream_team_repo
    if _dream_team_repo is None:
        _dream_team_repo = DreamTeamRepository()
    return _dream_team_repo


def get_custom_agent_repository() -> CustomAgentRepository:
    global _custom_agent_repo
    if _custom_agent_repo is None:
        _custom_agent_repo = CustomAgentRepository()
    return _custom_agent_repo


def get_memory_document_repository() -> MemoryDocumentRepository:
    global _memory_doc_repo
    if _memory_doc_repo is None:
        _memory_doc_repo = MemoryDocumentRepository()
    return _memory_doc_repo
