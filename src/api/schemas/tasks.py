from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.api.schemas.project import ProjectMetadataSchema
from src.schemas.models import ModelSelection


class WorkflowType(str, Enum):
    NEW_FEATURE = "new-feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"


class ModelOverrideSchema(BaseModel):
    agent: str
    provider: str
    model: str
    temperature: float | None = None
    max_tokens: int | None = None

    def to_selection(self) -> ModelSelection:
        return ModelSelection(
            agent=self.agent,
            provider=self.provider,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


class CreateSystemRequest(BaseModel):
    message: str = Field(..., min_length=3)
    project: ProjectMetadataSchema
    workflow: WorkflowType = WorkflowType.NEW_FEATURE
    project_id: str | None = None
    user_id: str | None = None
    models: list[ModelOverrideSchema] | None = None
    agents: list[str] | None = None


class ContinueTaskRequest(BaseModel):
    task_id: str
    message: str | None = None
    models: list[ModelOverrideSchema] | None = None


class TaskResponse(BaseModel):
    id: str
    status: str
    message: str = "Task aceita e em processamento"
    thread_id: str | None = None
    project_slug: str | None = None
    project_path: str | None = None


class TaskStepSchema(BaseModel):
    agent: str
    model_provider: str
    model_name: str
    model_source: str
    tokens_estimated: int
    latency_ms: int
    created_at: str | None = None


class TaskStatusResponse(BaseModel):
    id: str
    project_id: str
    project_slug: str | None = None
    project_path: str | None = None
    files_written_count: int = 0
    workflow: str
    demand: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    thread_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    steps: list[TaskStepSchema] = []


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    role: str = ""
    prompt_md: str = Field(..., min_length=10)
    model: ModelOverrideSchema
    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    restrictions: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    owner_id: str | None = None
    visibility: str = "private"


class AgentUpdateRequest(BaseModel):
    id: UUID
    name: str | None = None
    role: str | None = None
    prompt_md: str | None = None
    model: ModelOverrideSchema | None = None
    tools: list[str] | None = None
    permissions: list[str] | None = None
    restrictions: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    visibility: str | None = None


class AgentResponse(BaseModel):
    id: str
    slug: str
    name: str
    role: str
    default_provider: str
    default_model: str
    tools: list[str]
    permissions: list[str]
    restrictions: dict[str, Any]
    visibility: str
    is_custom: bool = True
    source: Literal["default", "file", "db"] = "db"
