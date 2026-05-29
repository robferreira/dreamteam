import asyncio
from functools import lru_cache
from typing import Any
from uuid import UUID

from src.cache.redis_client import get_redis_cache
from src.graph.checkpoint import get_thread_id
from src.graph.orchestrator import get_compiled_graph
from src.logging_config import get_logger
from src.memory.postgres import get_task_repository
from src.orchestrator.prompt_builder import PromptBuilder
from src.schemas.models import ModelSelection, ModelSource
from src.workflows.loader import load_workflow, parse_workflow_models

logger = get_logger(__name__)


class TaskService:
    def __init__(self) -> None:
        self._repo = get_task_repository()
        self._redis = get_redis_cache()

    def _serialize_models(self, models: list[ModelSelection] | None) -> list[dict[str, Any]]:
        if not models:
            return []
        return [m.model_dump(mode="json") for m in models]

    def _workflow_models_dict(
        self,
        workflow_name: str,
        team_models: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        if team_models:
            return team_models
        workflow = load_workflow(workflow_name)
        parsed = parse_workflow_models(workflow)
        return {k: v.model_dump(mode="json") for k, v in parsed.items()}

    def _build_workflow_config(self, workflow_name: str, agents: list[str]) -> dict[str, Any]:
        cfg = dict(load_workflow(workflow_name))
        required = [a for a in cfg.get("required_agents", []) if a in agents]
        specialists = [a for a in cfg.get("specialists", []) if a in agents]
        cfg["required_agents"] = required or cfg.get("required_agents", [])
        cfg["specialists"] = specialists or cfg.get("specialists", [])
        return cfg

    async def run_for_team(
        self,
        *,
        dream_team_id: UUID,
        project_uuid: UUID,
        project_slug: str,
        project_path: str,
        project_metadata: dict[str, Any],
        workflow: str,
        agents: list[str],
        team_models: dict[str, Any],
        prompt: str,
        user_id: str | None = None,
        user_models: list[ModelSelection] | None = None,
    ) -> dict[str, Any]:
        workflow_config = self._build_workflow_config(workflow, agents)
        enriched_demand = PromptBuilder.build_enriched_demand(prompt, project_metadata)

        task = await self._repo.create_task(
            workflow=workflow,
            demand=enriched_demand,
            project_id=project_slug,
            user_id=user_id,
            thread_id=None,
            project_uuid=project_uuid,
            dream_team_uuid=dream_team_id,
        )
        thread_id = get_thread_id(str(task.id))
        await self._repo.update_task(task.id, thread_id=thread_id)

        user_overrides = user_models or []
        for m in user_overrides:
            m.source = ModelSource.USER_API

        initial_state = {
            "task_id": str(task.id),
            "project_id": project_slug,
            "project_slug": project_slug,
            "project_path": project_path,
            "project_metadata": project_metadata,
            "dream_team_id": str(dream_team_id),
            "active_agents": agents,
            "user_id": user_id,
            "workflow_type": workflow,
            "demand": enriched_demand,
            "files_written_count": 0,
            "messages": [],
            "artifacts": {},
            "visited_agents": [],
            "specialists_done": [],
            "iteration_count": 0,
            "revision_count": 0,
            "needs_architecture": workflow_config.get("needs_architecture_default", False),
            "workflow_config": workflow_config,
            "workflow_models": self._workflow_models_dict(workflow, team_models),
            "user_model_overrides": self._serialize_models(user_overrides),
            "orchestrator_model_overrides": [],
            "specialists_pending": [
                a for a in workflow_config.get("specialists", []) if a in agents
            ],
            "force_stop": False,
            "force_economy": False,
        }

        asyncio.create_task(self._run_graph(task.id, initial_state, thread_id))
        await self._redis.publish_event(
            f"task:{task.id}",
            {"type": "started", "task_id": str(task.id)},
        )

        return {
            "task_id": str(task.id),
            "id": str(task.id),
            "status": "running",
            "message": "Execução iniciada",
            "thread_id": thread_id,
            "project_slug": project_slug,
            "project_path": f"projects/{project_slug}",
        }

    async def continue_task(
        self,
        task_id: UUID,
        message: str | None = None,
        models: list[ModelSelection] | None = None,
    ) -> dict[str, Any]:
        task = await self._repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task não encontrada: {task_id}")

        redis = get_redis_cache()
        lock_key = str(task_id)
        if not await redis.acquire_lock(lock_key):
            raise ValueError("Task em processamento por outra requisição")

        try:
            thread_id = task.thread_id or get_thread_id(str(task.id))
            graph = await get_compiled_graph()

            config = {"configurable": {"thread_id": thread_id}}
            user_overrides = self._serialize_models(models)

            if message:
                await graph.aupdate_state(
                    config,
                    {
                        "demand": f"{task.demand}\n\nContinuação: {message}",
                        "user_model_overrides": user_overrides,
                    },
                )
            elif user_overrides:
                await graph.aupdate_state(
                    config,
                    {"user_model_overrides": user_overrides},
                )

            await self._repo.update_task(task_id, status="running")
            asyncio.create_task(self._resume_graph(task_id, thread_id))
            return {"id": str(task_id), "status": "running", "message": "Task retomada"}
        finally:
            await redis.release_lock(lock_key)

    async def get_task(self, task_id: UUID) -> dict[str, Any] | None:
        task = await self._repo.get_task_with_steps(task_id)
        if not task:
            return None
        steps = [
            {
                "agent": s.agent,
                "model_provider": s.model_provider,
                "model_name": s.model_name,
                "model_source": s.model_source,
                "tokens_estimated": s.tokens_estimated,
                "latency_ms": s.latency_ms,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in (task.steps or [])
        ]
        result = task.result or {}
        return {
            "id": str(task.id),
            "project_id": task.project_id,
            "project_slug": task.project_id,
            "project_path": result.get("project_path"),
            "files_written_count": result.get("files_written_count", 0),
            "workflow": task.workflow,
            "demand": task.demand,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "thread_id": task.thread_id,
            "dream_team_id": str(task.dream_team_uuid) if task.dream_team_uuid else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "steps": steps,
        }

    async def _run_graph(self, task_id: UUID, initial_state: dict, thread_id: str) -> None:
        try:
            graph = await get_compiled_graph()
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke(initial_state, config)
            final = result.get("final_result", result)
            status = "completed" if final.get("approved") or result.get("memory_result") else "completed_with_issues"
            await self._repo.update_task(task_id, status=status, result=final)
            await self._redis.publish_event(
                f"task:{task_id}",
                {"type": "completed", "task_id": str(task_id), "status": status},
            )
            logger.info("task_completed", task_id=str(task_id), status=status)
        except Exception as e:
            logger.error("task_failed", task_id=str(task_id), error=str(e))
            await self._repo.update_task(task_id, status="failed", error=str(e))
            await self._redis.publish_event(
                f"task:{task_id}",
                {"type": "failed", "task_id": str(task_id), "error": str(e)},
            )

    async def _resume_graph(self, task_id: UUID, thread_id: str) -> None:
        try:
            graph = await get_compiled_graph()
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke(None, config)
            final = result.get("final_result", result)
            status = "completed" if final.get("approved") or result.get("memory_result") else "completed_with_issues"
            await self._repo.update_task(task_id, status=status, result=final)
        except Exception as e:
            await self._repo.update_task(task_id, status="failed", error=str(e))


@lru_cache
def get_task_service() -> TaskService:
    return TaskService()
