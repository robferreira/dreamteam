import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.dream_teams.service import DreamTeamService


@pytest.mark.asyncio
async def test_work_your_magic_skips_legacy_slug_and_creates_new_team():
    svc = DreamTeamService()
    team_id = uuid4()
    project_id = uuid4()

    legacy_project = MagicMock()
    legacy_project.id = project_id
    legacy_project.slug = "sistema-de-agentes-dreamteam-4"

    legacy_team = MagicMock()
    legacy_team.id = team_id
    legacy_team.status = "ready"
    legacy_team.workflow = "new-feature"
    legacy_team.agents = ["backend"]
    legacy_team.project_uuid = project_id
    legacy_team.slug = legacy_project.slug

    new_team_id = uuid4()
    run_payload = {
        "task_id": str(uuid4()),
        "project_slug": "dt_sistema-de-agentes",
        "project_path": "projects/dt_sistema-de-agentes",
        "status": "running",
    }

    svc._project_repo = MagicMock()
    svc._project_repo.get_by_sigla = AsyncMock(return_value=legacy_project)
    svc._repo = MagicMock()
    svc._repo.get_by_project = AsyncMock(return_value=legacy_team)
    svc.create_team = AsyncMock(
        return_value={
            "dream_team_id": str(new_team_id),
            "project_slug": "dt_sistema-de-agentes",
            "project_path": "projects/dt_sistema-de-agentes",
        }
    )
    svc._repo.get_by_id = AsyncMock(
        side_effect=lambda tid: legacy_team if tid == new_team_id else legacy_team
    )
    svc.run_team = AsyncMock(return_value=run_payload)

    result = await svc.work_your_magic(
        pedido="Criar sistema de agentes com API REST",
        responsavel="Maria",
        sigla="DT",
        nome_projeto="Sistema de Agentes",
    )

    svc.create_team.assert_awaited_once()
    svc.run_team.assert_awaited_once()
    assert result["project_slug"] == "dt_sistema-de-agentes"
