import re

from pydantic import BaseModel, Field, field_validator

from src.api.schemas.project import ProjectMetadataSchema
from src.api.schemas.tasks import ModelOverrideSchema, TaskTimelineSchema, WorkflowType


class CreateDreamTeamRequest(BaseModel):
    project: ProjectMetadataSchema
    workflow: WorkflowType | None = None
    agents: list[str] | None = None
    models: list[ModelOverrideSchema] | None = None
    user_id: str | None = None


class DreamTeamResponse(BaseModel):
    dream_team_id: str
    project_slug: str
    project_path: str
    workflow: str
    agents: list[str]
    status: str = "ready"


class RunDreamTeamRequest(BaseModel):
    prompt: str = Field(..., min_length=3)
    models: list[ModelOverrideSchema] | None = None


class RunDreamTeamResponse(BaseModel):
    task_id: str
    dream_team_id: str
    project_slug: str
    project_path: str
    status: str
    message: str = "Execução iniciada"
    timeline: TaskTimelineSchema | None = None


class WorkYourMagicRequest(BaseModel):
    """Demanda do usuário + dados que o sistema não consegue inferir com segurança."""

    pedido: str = Field(
        ...,
        min_length=3,
        description="O que você precisa (demanda técnica)",
        examples=["Criar API REST de estoque com PostgreSQL e testes automatizados"],
    )
    responsavel: str = Field(
        ...,
        min_length=2,
        max_length=256,
        description="Nome do responsável pelo projeto",
        examples=["Maria Silva"],
    )
    sigla: str = Field(
        ...,
        min_length=2,
        max_length=16,
        description="Sigla única do projeto (ex.: ESTQ, PAGTO)",
        examples=["ESTQ"],
    )
    nome_projeto: str | None = Field(
        default=None,
        min_length=2,
        max_length=256,
        description="Nome do projeto. Se omitido, é inferido a partir do pedido",
        examples=["Sistema de Estoque ACME"],
    )
    descricao: str | None = Field(
        default=None,
        min_length=10,
        description="Descrição do projeto. Se omitida, usa o texto do pedido",
        examples=["Plataforma para controle de estoque e movimentações"],
    )

    @field_validator("sigla")
    @classmethod
    def normalize_sigla(cls, v: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9-]", "", v.strip().upper())
        if len(cleaned) < 2:
            raise ValueError("Sigla deve ter ao menos 2 caracteres alfanuméricos")
        return cleaned


class WorkYourMagicResponse(BaseModel):
    task_id: str
    dream_team_id: str
    project_slug: str
    project_path: str
    workflow: str
    agents: list[str]
    rationale: str
    status: str
    timeline: TaskTimelineSchema | None = None
