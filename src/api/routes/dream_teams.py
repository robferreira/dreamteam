from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.api.schemas.dream_team import (
    CreateDreamTeamRequest,
    DreamTeamResponse,
    RunDreamTeamRequest,
    RunDreamTeamResponse,
)
from src.dream_teams.service import get_dream_team_service

router = APIRouter()


@router.post("", response_model=DreamTeamResponse)
async def create_dream_team(request: CreateDreamTeamRequest):
    svc = get_dream_team_service()
    workflow = request.workflow.value if request.workflow else None
    result = await svc.create_team(
        project=request.project,
        workflow=workflow,
        agents=request.agents,
        models=request.models,
        user_id=request.user_id,
        matcher_source="manual",
    )
    return DreamTeamResponse(**result)


@router.post("/{team_id}/run", response_model=RunDreamTeamResponse)
async def run_dream_team(team_id: str, request: RunDreamTeamRequest):
    svc = get_dream_team_service()
    try:
        uid = UUID(team_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="team_id inválido") from e

    try:
        result = await svc.run_team(uid, request.prompt, models=request.models)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RunDreamTeamResponse(
        task_id=result["task_id"],
        dream_team_id=team_id,
        project_slug=result["project_slug"],
        project_path=result["project_path"],
        status=result["status"],
        message=result.get("message", "Execução iniciada"),
        timeline=result.get("timeline"),
    )
