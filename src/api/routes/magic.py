from fastapi import APIRouter, HTTPException

from src.api.schemas.dream_team import WorkYourMagicRequest, WorkYourMagicResponse
from src.dream_teams.service import get_dream_team_service

router = APIRouter()


@router.post("", response_model=WorkYourMagicResponse)
async def work_your_magic(request: WorkYourMagicRequest):
    svc = get_dream_team_service()
    try:
        result = await svc.work_your_magic(
            pedido=request.pedido,
            responsavel=request.responsavel,
            sigla=request.sigla,
            nome_projeto=request.nome_projeto,
            descricao=request.descricao,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return WorkYourMagicResponse(
        task_id=result["task_id"],
        dream_team_id=result["dream_team_id"],
        project_slug=result["project_slug"],
        project_path=result["project_path"],
        workflow=result["workflow"] or "",
        agents=result["agents"] or [],
        rationale=result["rationale"],
        status=result["status"],
    )
