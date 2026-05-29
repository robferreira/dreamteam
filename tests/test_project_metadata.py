import pytest
from pydantic import ValidationError

from src.api.schemas.project import ProjectMetadataSchema


def test_valid_metadata():
    m = ProjectMetadataSchema(
        system_name="App",
        system_description="Descrição longa do sistema",
        owner_name="Maria",
        owner_email="maria@test.com",
        area="financeiro",
    )
    assert m.system_name == "App"
    assert "maria@test.com" in m.to_metadata_dict()["owner_email"]


def test_invalid_email():
    with pytest.raises(ValidationError):
        ProjectMetadataSchema(
            system_name="App",
            system_description="Descrição longa do sistema",
            owner_name="Maria",
            owner_email="not-an-email",
            area="financeiro",
        )


def test_short_description_rejected():
    with pytest.raises(ValidationError):
        ProjectMetadataSchema(
            system_name="App",
            system_description="curta",
            owner_name="Maria",
            owner_email="maria@test.com",
            area="financeiro",
        )
