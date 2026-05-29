from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tasks.service import TaskService


def _make_step(agent: str, created_at: datetime):
    step = MagicMock()
    step.agent = agent
    step.model_provider = "openai"
    step.model_name = "gpt-4o-mini"
    step.model_source = "workflow"
    step.tokens_estimated = 100
    step.latency_ms = 50
    step.output = {"ok": True}
    step.created_at = created_at
    return step


@pytest.mark.asyncio
async def test_get_task_includes_running_step():
    task_id = uuid4()
    now = datetime.now(UTC)
    task = MagicMock()
    task.id = task_id
    task.project_id = "proj"
    task.workflow = "new-feature"
    task.demand = "test"
    task.status = "running"
    task.result = None
    task.error = None
    task.thread_id = "thread"
    task.dream_team_uuid = None
    task.created_at = now
    task.updated_at = now
    task.timeline = None
    task.current_agent = "frontend"
    task.steps = [_make_step("backend", now)]

    svc = TaskService()
    svc._repo = AsyncMock()
    svc._redis = AsyncMock()
    svc._repo.get_task_with_steps = AsyncMock(return_value=task)
    svc._redis.has_task_heartbeat = AsyncMock(return_value=True)

    data = await svc.get_task(task_id)
    assert data["status"] == "running"
    assert data["current_agent"] == "frontend"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["status"] == "completed"
    assert data["steps"][1]["status"] == "running"
    assert data["steps"][1]["agent"] == "frontend"
    assert data["progress"]["current_agent"] == "frontend"


@pytest.mark.asyncio
async def test_stale_task_marked_interrupted():
    task_id = uuid4()
    old = datetime(2020, 1, 1, tzinfo=UTC)
    task_running = MagicMock()
    task_running.id = task_id
    task_running.project_id = "proj"
    task_running.workflow = "new-feature"
    task_running.demand = "test"
    task_running.status = "running"
    task_running.result = None
    task_running.error = None
    task_running.thread_id = "thread"
    task_running.dream_team_uuid = None
    task_running.created_at = old
    task_running.updated_at = old
    task_running.timeline = None
    task_running.current_agent = None
    task_running.steps = [_make_step("backend", old)]

    task_interrupted = MagicMock()
    task_interrupted.id = task_id
    task_interrupted.project_id = "proj"
    task_interrupted.workflow = "new-feature"
    task_interrupted.demand = "test"
    task_interrupted.status = "interrupted"
    task_interrupted.result = None
    task_interrupted.error = "Execução interrompida: serviço reiniciado ou worker inativo"
    task_interrupted.thread_id = "thread"
    task_interrupted.dream_team_uuid = None
    task_interrupted.created_at = old
    task_interrupted.updated_at = old
    task_interrupted.timeline = None
    task_interrupted.current_agent = None
    task_interrupted.steps = [_make_step("backend", old)]

    svc = TaskService()
    svc._repo = AsyncMock()
    svc._redis = AsyncMock()
    svc._repo.get_task_with_steps = AsyncMock(side_effect=[task_running, task_interrupted])
    svc._repo.mark_interrupted = AsyncMock()
    svc._redis.has_task_heartbeat = AsyncMock(return_value=False)
    svc._redis.clear_task_heartbeat = AsyncMock()

    with patch("src.tasks.service.get_settings") as mock_settings:
        mock_settings.return_value.request_timeout_seconds = 120
        data = await svc.get_task(task_id)

    svc._repo.mark_interrupted.assert_awaited_once()
    assert data["status"] == "interrupted"
