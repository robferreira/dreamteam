import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("src.memory.postgres.init_db", new=AsyncMock()):
        from src.main import app

        with TestClient(app) as c:
            yield c


def test_work_your_magic_minimal_body(client):
    task_id = str(uuid4())
    team_id = str(uuid4())
    with patch(
        "src.dream_teams.service.DreamTeamService.work_your_magic",
        new=AsyncMock(
            return_value={
                "task_id": task_id,
                "dream_team_id": team_id,
                "project_slug": "estq",
                "project_path": "projects/estq",
                "workflow": "new-feature",
                "agents": ["requirements", "backend"],
                "rationale": "Nova feature com backend",
                "status": "running",
            }
        ),
    ):
        r = client.post(
            "/work-your-magic",
            json={
                "pedido": "Criar API REST de estoque com PostgreSQL e testes",
                "responsavel": "Maria Silva",
                "sigla": "ESTQ",
            },
        )
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_work_your_magic_requires_responsavel_and_sigla(client):
    r = client.post(
        "/work-your-magic",
        json={"pedido": "Criar API de estoque"},
    )
    assert r.status_code == 422


def test_work_your_magic_normalizes_sigla():
    from src.api.schemas.dream_team import WorkYourMagicRequest

    req = WorkYourMagicRequest(
        pedido="Criar API REST de estoque com PostgreSQL",
        responsavel="Maria",
        sigla=" estq ",
    )
    assert req.sigla == "ESTQ"


def test_create_system_deprecated(client):
    r = client.post("/tasks/create-system", json={})
    assert r.status_code == 410
