import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.schemas.project import ProjectMetadataSchema
from src.projects.service import ProjectService, slugify


def test_slugify():
    assert slugify("Sistema de Pagamentos ACME") == "sistema-de-pagamentos-acme"


@pytest.fixture
def sample_project():
    return ProjectMetadataSchema(
        system_name="Test System",
        system_description="A test system for unit tests",
        owner_name="João Teste",
        owner_email="joao@test.com",
        area="ti",
        organization="Test Corp",
        stack_hint="python-fastapi",
    )


@pytest.mark.asyncio
async def test_create_project_files(tmp_path, sample_project):
    with patch("src.projects.service.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(projects_dir=tmp_path)
        with patch.object(ProjectService, "_unique_slug", new=AsyncMock(return_value="test-system")):
            mock_repo = MagicMock()
            row = MagicMock()
            row.id = "00000000-0000-0000-0000-000000000001"
            mock_repo.create = AsyncMock(return_value=row)
            svc = ProjectService()
            svc._repo = mock_repo

            result = await svc.create_project(sample_project)

    assert result["slug"] == "test-system"
    project_dir = tmp_path / "test-system"
    assert (project_dir / "project.json").exists()
    assert (project_dir / "README.md").exists()
    assert "Test System" in (project_dir / "README.md").read_text(encoding="utf-8")
