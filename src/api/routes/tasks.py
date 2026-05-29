from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.api.schemas.tasks import (
    ContinueTaskRequest,
    TaskResponse,
    TaskStatusResponse,
    TaskStepSchema,
)
from src.orchestrator.service import get_orchestrator_service

router = APIRouter()


@router.post("/create-system", deprecated=True)
async def create_system_deprecated():
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Rota descontinuada. Use POST /dream-teams para configurar o time e POST /dream-teams/{id}/run para executar com prompt, ou POST /work-your-magic para fluxo completo.",
            "alternatives": {
                "setup": "POST /dream-teams",
                "run": "POST /dream-teams/{id}/run",
                "magic": "POST /work-your-magic",
            },
        },
    )


@router.post("/continue", response_model=TaskResponse)
async def continue_task(request: ContinueTaskRequest):
    orchestrator = get_orchestrator_service()
    models = [m.to_selection() for m in (request.models or [])]
    try:
        result = await orchestrator.continue_task(
            task_id=request.task_id,
            message=request.message,
            models=models,
        )
        return TaskResponse(id=result["id"], status=result["status"], message=result.get("message", ""))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    from src.tasks.service import get_task_service

    try:
        uid = UUID(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="task_id inválido") from e

    data = await get_task_service().get_task(uid)
    if not data:
        raise HTTPException(status_code=404, detail="Task não encontrada")

    steps = [TaskStepSchema(**s) for s in data.get("steps", [])]
    return TaskStatusResponse(**{**data, "steps": steps})
