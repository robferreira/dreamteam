from functools import lru_cache
from uuid import UUID

from src.schemas.models import ModelSelection


class OrchestratorService:
    """Facade fino para continue de tasks."""

    def __init__(self) -> None:
        from src.tasks.service import get_task_service

        self._tasks = get_task_service()

    async def continue_task(
        self,
        task_id: str,
        message: str | None = None,
        models: list[ModelSelection] | None = None,
    ) -> dict:
        return await self._tasks.continue_task(UUID(task_id), message=message, models=models)


@lru_cache
def get_orchestrator_service() -> OrchestratorService:
    return OrchestratorService()
