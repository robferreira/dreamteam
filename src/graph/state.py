import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import add_messages

from src.schemas.models import ModelSelection

AgentName = Literal[
    "orchestrator",
    "requirements",
    "architect",
    "planner",
    "backend",
    "frontend",
    "database",
    "devops",
    "security",
    "documentation",
    "reviewer",
    "memory",
    "monitoring",
    "cost_optimizer",
    "specialists_parallel",
    "FINISH",
]


class AgentState(TypedDict, total=False):
    task_id: str
    project_id: str
    user_id: str | None
    workflow_type: str
    demand: str
    messages: Annotated[list, add_messages]
    specification: dict[str, Any]
    architecture: dict[str, Any]
    task_plan: dict[str, Any]
    artifacts: dict[str, Any]
    review_result: dict[str, Any]
    memory_result: dict[str, Any]
    monitoring_result: dict[str, Any]
    cost_result: dict[str, Any]
    needs_architecture: bool
    current_agent: str
    next_agent: str
    visited_agents: Annotated[list[str], operator.add]
    iteration_count: int
    revision_count: int
    specialists_pending: list[str]
    specialists_done: Annotated[list[str], operator.add]
    workflow_config: dict[str, Any]
    workflow_models: dict[str, dict[str, Any]]
    user_model_overrides: list[dict[str, Any]]
    orchestrator_model_overrides: list[dict[str, Any]]
    force_economy: bool
    final_result: dict[str, Any]
    force_stop: bool
    error: str
    parallel_batch_id: str | None
    project_metadata: dict[str, Any]
    project_path: str
    project_slug: str
    files_written_count: int
    dream_team_id: str
    active_agents: list[str]


def models_from_state(state: AgentState) -> dict[str, ModelSelection]:
    raw = state.get("workflow_models") or {}
    result: dict[str, ModelSelection] = {}
    for agent, cfg in raw.items():
        if isinstance(cfg, dict):
            result[agent] = ModelSelection(**{**cfg, "agent": agent})
        elif isinstance(cfg, ModelSelection):
            result[agent] = cfg
    return result


def user_models_from_state(state: AgentState) -> list[ModelSelection]:
    raw = state.get("user_model_overrides") or []
    return [ModelSelection(**m) if isinstance(m, dict) else m for m in raw]
