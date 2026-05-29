import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

SAMPLE_PROJECT = {
    "system_name": "Sistema Teste",
    "system_description": "Descrição completa do sistema de testes automatizados",
    "owner_name": "Maria Silva",
    "owner_email": "maria@test.com",
    "area": "financeiro",
    "organization": "ACME",
    "stack_hint": "python-fastapi",
}


@pytest.fixture
def client():
    with patch("src.memory.postgres.init_db", new=AsyncMock()):
        from src.main import app

        with TestClient(app) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_workflows(client):
    r = client.get("/workflows")
    assert r.status_code == 200
    assert "new-feature" in r.json()["workflows"]


def test_create_dream_team_mocked(client):
    team_id = str(uuid4())
    with patch(
        "src.dream_teams.service.DreamTeamService.create_team",
        new=AsyncMock(
            return_value={
                "dream_team_id": team_id,
                "project_slug": "sistema-teste",
                "project_path": "projects/sistema-teste",
                "workflow": "new-feature",
                "agents": ["requirements", "backend"],
                "status": "ready",
            }
        ),
    ):
        r = client.post(
            "/dream-teams",
            json={"project": SAMPLE_PROJECT, "workflow": "new-feature"},
        )
    assert r.status_code == 200
    assert r.json()["dream_team_id"] == team_id
    assert r.json()["status"] == "ready"


def test_run_dream_team_mocked(client):
    team_id = str(uuid4())
    task_id = str(uuid4())
    with patch(
        "src.dream_teams.service.DreamTeamService.run_team",
        new=AsyncMock(
            return_value={
                "task_id": task_id,
                "project_slug": "sistema-teste",
                "project_path": "projects/sistema-teste",
                "status": "running",
                "message": "Execução iniciada",
            }
        ),
    ):
        r = client.post(
            f"/dream-teams/{team_id}/run",
            json={"prompt": "Adicionar módulo de relatórios PDF"},
        )
    assert r.status_code == 200
    assert r.json()["task_id"] == task_id
    assert r.json()["status"] == "running"


def test_create_system_deprecated(client):
    r = client.post("/tasks/create-system")
    assert r.status_code == 410


def test_get_agent_system(client):
    r = client.get("/agents/backend")
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == "backend"
