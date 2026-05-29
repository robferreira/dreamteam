from fastapi import APIRouter, HTTPException

from src.api.schemas.project import ProjectResponse
from src.projects.service import get_project_service

router = APIRouter()


@router.get("/{slug}", response_model=ProjectResponse)
async def get_project(slug: str):
    svc = get_project_service()
    row = await svc.get_project(slug)
    if not row:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    files = svc.list_project_files(slug)
    return ProjectResponse(
        id=str(row.id),
        slug=row.slug,
        system_name=row.system_name,
        system_description=row.system_description,
        owner_name=row.owner_name,
        owner_email=row.owner_email,
        area=row.area,
        organization=row.organization,
        stack_hint=row.stack_hint,
        stack_resolved=row.stack_resolved,
        root_path=row.root_path,
        files=files,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )
