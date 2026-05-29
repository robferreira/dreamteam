from typing import Any

from pydantic import BaseModel, Field


class ArtifactItem(BaseModel):
    type: str
    path: str
    content: str
    description: str = ""


class IssueItem(BaseModel):
    severity: str
    description: str
    agent: str = ""


class RefactorRequest(BaseModel):
    agent: str
    reason: str


class RequirementsOutput(BaseModel):
    needs_architecture: bool = True
    functional_requirements: list[dict[str, Any]] = Field(default_factory=list)
    non_functional_requirements: list[dict[str, Any]] = Field(default_factory=list)
    user_stories: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    notes: str = ""
    error: str | None = None


class ArchitectOutput(BaseModel):
    stack: str = ""
    structure: dict[str, Any] = Field(default_factory=dict)
    components: list[dict[str, Any]] = Field(default_factory=list)
    apis: list[dict[str, Any]] = Field(default_factory=list)
    data_model: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    error: str | None = None


class PlannerTask(BaseModel):
    id: str = ""
    agent: str
    description: str = ""
    priority: int = 1


class PlannerOutput(BaseModel):
    tasks: list[PlannerTask] = Field(default_factory=list)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""
    error: str | None = None


class SpecialistOutput(BaseModel):
    model_config = {"extra": "allow"}
    artifacts: list[ArtifactItem] = Field(default_factory=list)
    apis: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""
    error: str | None = None


class ReviewerOutput(BaseModel):
    approved: bool = False
    issues: list[IssueItem] = Field(default_factory=list)
    refactor_requests: list[RefactorRequest] = Field(default_factory=list)
    notes: str = ""
    error: str | None = None


class MemoryDocument(BaseModel):
    type: str = "memory"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryOutput(BaseModel):
    documents: list[MemoryDocument] = Field(default_factory=list)
    notes: str = ""
    error: str | None = None


class GenericOutput(BaseModel):
    model_config = {"extra": "allow"}
    error: str | None = None


AGENT_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "requirements": RequirementsOutput,
    "architect": ArchitectOutput,
    "planner": PlannerOutput,
    "backend": SpecialistOutput,
    "frontend": SpecialistOutput,
    "database": SpecialistOutput,
    "devops": SpecialistOutput,
    "security": SpecialistOutput,
    "documentation": SpecialistOutput,
    "reviewer": ReviewerOutput,
    "memory": MemoryOutput,
}


SPECIALIST_AGENTS = {"backend", "frontend", "database", "devops", "security", "documentation"}


def get_output_schema(agent_name: str) -> type[BaseModel] | None:
    return AGENT_OUTPUT_SCHEMAS.get(agent_name)


def validate_agent_output(agent_name: str, output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if output.get("parse_error"):
        return output, ["Resposta não é JSON válido"]
    if output.get("error"):
        return output, []

    schema = get_output_schema(agent_name)
    if not schema:
        try:
            validated = GenericOutput.model_validate(output)
            return validated.model_dump(), []
        except Exception as exc:
            return output, [str(exc)]

    try:
        validated = schema.model_validate(output)
        return validated.model_dump(), []
    except Exception as exc:
        return output, [str(exc)]


def has_high_severity_issues(review_output: dict[str, Any]) -> bool:
    issues = review_output.get("issues", [])
    if not isinstance(issues, list):
        return False
    return any(
        isinstance(issue, dict) and str(issue.get("severity", "")).lower() == "high"
        for issue in issues
    )
