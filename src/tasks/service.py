import asyncio
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID

from src.cache.redis_client import get_redis_cache
from src.dream_teams.timeline_estimator import estimate_timeline
from src.graph.checkpoint import get_thread_id
from src.graph.orchestrator import get_compiled_graph
from src.logging_config import get_logger
from src.memory.postgres import get_task_repository
from src.orchestrator.prompt_builder import PromptBuilder
from src.schemas.models import ModelSelection, ModelSource
from src.settings import get_settings
from src.tasks.reconciliation import INTERRUPTED_MESSAGE
from src.utils.datetime_display import format_display_datetime
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

    def _step_status(self, output: dict[str, Any] | None) -> str:
        if isinstance(output, dict) and output.get("error"):
            return "failed"
        return "completed"

    def _build_steps_response(
        self,
        task,
        *,
        status: str,
        current_agent: str | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        steps: list[dict[str, Any]] = []
        for s in sorted(task.steps or [], key=lambda x: x.created_at or datetime(1970, 1, 1, tzinfo=UTC)):
            steps.append(
                {
                    "agent": s.agent,
                    "status": self._step_status(s.output),
                    "model_provider": s.model_provider,
                    "model_name": s.model_name,
                    "model_source": s.model_source,
                    "tokens_estimated": s.tokens_estimated,
                    "latency_ms": s.latency_ms,
                    "created_at": format_display_datetime(s.created_at)
                    if s.created_at
                    else None,
                }
            )

        progress: dict[str, Any] | None = None
        if status == "running" and current_agent:
            if not (
                steps
                and steps[-1]["status"] == "running"
                and steps[-1]["agent"] == current_agent
            ):
                steps.append(
                    {
                        "agent": current_agent,
                        "status": "running",
                        "model_provider": "",
                        "model_name": "",
                        "model_source": "",
                        "tokens_estimated": 0,
                        "latency_ms": 0,
                        "created_at": None,
                    }
                )
            progress = {
                "completed_count": len([s for s in steps if s["status"] == "completed"]),
                "current_agent": current_agent,
                "label": f"{current_agent} em execução",
            }

        return steps, progress

    async def _maybe_reconcile_stale_task(self, task) -> str:
        if task.status != "running":
            return task.status

        has_heartbeat = await self._redis.has_task_heartbeat(str(task.id))
        if has_heartbeat:
            return task.status

        stale_threshold = get_settings().request_timeout_seconds * 2
        last_activity = task.created_at
        if task.steps:
            last_step = max(task.steps, key=lambda s: s.created_at or task.created_at)
            if last_step.created_at:
                last_activity = last_step.created_at

        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=UTC)
        elapsed = (datetime.now(UTC) - last_activity.astimezone(UTC)).total_seconds()
        if elapsed <= stale_threshold:
            return task.status

        await self._repo.mark_interrupted(task.id, error=INTERRUPTED_MESSAGE)
        await self._redis.clear_task_heartbeat(str(task.id))
        logger.warning("stale_task_reconciled", task_id=str(task.id), elapsed_seconds=int(elapsed))
        return "interrupted"

    async def _clear_task_worker_state(self, task_id: UUID) -> None:
        await self._redis.clear_task_heartbeat(str(task_id))
        await self._repo.update_task(task_id, clear_current_agent=True)

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
        timeline_estimate = estimate_timeline(prompt=prompt, workflow=workflow, agents=agents)
        timeline_dict = timeline_estimate.to_dict()

        metadata = dict(project_metadata)
        extra = dict(metadata.get("additional_context") or {})
        extra["timeline"] = timeline_dict
        metadata["additional_context"] = extra

        enriched_demand = PromptBuilder.build_enriched_demand(prompt, metadata)

        task = await self._repo.create_task(
            workflow=workflow,
            demand=enriched_demand,
            project_id=project_slug,
            user_id=user_id,
            thread_id=None,
            project_uuid=project_uuid,
            dream_team_uuid=dream_team_id,
            timeline=timeline_dict,
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
            "project_metadata": metadata,
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
            "timeline": timeline_dict,
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

        status = await self._maybe_reconcile_stale_task(task)
        if status != task.status:
            task = await self._repo.get_task_with_steps(task_id)
            if not task:
                return None

        steps, progress = self._build_steps_response(
            task,
            status=status,
            current_agent=task.current_agent,
        )
        result = task.result or {}
        timeline = task.timeline
        if isinstance(timeline, dict) and task.created_at:
            timeline = dict(timeline)

        return {
            "id": str(task.id),
            "project_id": task.project_id,
            "project_slug": task.project_id,
            "project_path": result.get("project_path"),
            "files_written_count": result.get("files_written_count", 0),
            "workflow": task.workflow,
            "demand": task.demand,
            "status": status,
            "result": task.result,
            "error": task.error,
            "thread_id": task.thread_id,
            "dream_team_id": str(task.dream_team_uuid) if task.dream_team_uuid else None,
            "created_at": format_display_datetime(task.created_at) if task.created_at else None,
            "updated_at": format_display_datetime(task.updated_at) if task.updated_at else None,
            "timeline": timeline,
            "current_agent": task.current_agent if status == "running" else None,
            "progress": progress,
            "steps": steps,
        }

    async def _run_graph(self, task_id: UUID, initial_state: dict, thread_id: str) -> None:
        try:
            graph = await get_compiled_graph()
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke(initial_state, config)
            final = result.get("final_result", result)
            status = "completed" if final.get("approved") or result.get("memory_result") else "completed_with_issues"
            await self._repo.update_task(task_id, status=status, result=final, clear_current_agent=True)
            await self._redis.publish_event(
                f"task:{task_id}",
                {"type": "completed", "task_id": str(task_id), "status": status},
            )
            logger.info("task_completed", task_id=str(task_id), status=status)
        except Exception as e:
            logger.error("task_failed", task_id=str(task_id), error=str(e))
            await self._repo.update_task(
                task_id,
                status="failed",
                error=str(e),
                clear_current_agent=True,
            )
            await self._redis.publish_event(
                f"task:{task_id}",
                {"type": "failed", "task_id": str(task_id), "error": str(e)},
            )
        finally:
            await self._clear_task_worker_state(task_id)

    async def _resume_graph(self, task_id: UUID, thread_id: str) -> None:
        try:
            graph = await get_compiled_graph()
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke(None, config)
            final = result.get("final_result", result)
            status = "completed" if final.get("approved") or result.get("memory_result") else "completed_with_issues"
            await self._repo.update_task(task_id, status=status, result=final, clear_current_agent=True)
        except Exception as e:
            await self._repo.update_task(
                task_id,
                status="failed",
                error=str(e),
                clear_current_agent=True,
            )
        finally:
            await self._clear_task_worker_state(task_id)


@lru_cache
def get_task_service() -> TaskService:
    return TaskService()
