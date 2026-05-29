from src.dream_teams.demand_parser import (
    build_project_from_demand,
    infer_stack_hint,
    project_slug_from_sigla,
)


def test_infer_stack_from_prompt():
    assert infer_stack_hint("API REST em Python com FastAPI e PostgreSQL") == "python-fastapi"


def test_build_project_with_explicit_fields():
    project = build_project_from_demand(
        pedido="Criar API REST de estoque com PostgreSQL",
        responsavel="Maria Silva",
        sigla="ESTQ",
        nome_projeto="Sistema de Estoque",
        descricao="Plataforma de controle de estoque e movimentações",
    )
    assert project.system_name == "Sistema de Estoque"
    assert project.system_description.startswith("Plataforma")
    assert project.owner_name == "Maria Silva"
    assert project.organization == "ESTQ"
    assert project.additional_context["sigla"] == "ESTQ"
    assert project.additional_context.get("nome_projeto_inferred") is None


def test_build_project_infers_name_and_description():
    pedido = "Criar sistema de estoque com API REST e PostgreSQL"
    project = build_project_from_demand(
        pedido=pedido,
        responsavel="João",
        sigla="ESTQ",
    )
    assert project.system_name == pedido
    assert project.system_description == pedido
    assert project.additional_context["nome_projeto_inferred"] is True
    assert project.additional_context["descricao_inferred"] is True
    assert project.stack_hint == "python-fastapi"


def test_slug_from_sigla():
    assert project_slug_from_sigla("ESTQ") == "estq"
