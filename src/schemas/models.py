from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelSource(str, Enum):
    RUNTIME = "runtime"
    WORKFLOW = "workflow"
    USER_API = "user_api"
    AGENT_DEFAULT = "agent_default"
    SYSTEM_DEFAULT = "system_default"
    ORCHESTRATOR_OVERRIDE = "orchestrator_override"


class ModelSelection(BaseModel):
    agent: str
    provider: str
    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    source: ModelSource = ModelSource.RUNTIME


class DefaultModelConfig(BaseModel):
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int | None = None


class AgentOverrideRules(BaseModel):
    allow_providers: list[str] = Field(default_factory=list)
    max_cost_tier: str = "standard"


class AgentDefinition(BaseModel):
    name: str
    role: str = ""
    capabilities: list[str] = Field(default_factory=list)
    default_model: DefaultModelConfig
    override_rules: AgentOverrideRules = Field(default_factory=AgentOverrideRules)
    raw_prompt: str = ""
    is_custom: bool = False
    skills: list[str] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    reject_if: list[str] = Field(default_factory=list)
    output_schema_ref: str = ""
    tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    restrictions: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    owner_id: str | None = None
    visibility: Literal["private", "shared", "public"] = "private"

    @property
    def effective_plugins(self) -> list[str]:
        """Unifica plugins declarados e tools (alias para agentes custom)."""
        merged = list(self.plugins)
        for tool in self.tools:
            if tool not in merged:
                merged.append(tool)
        return merged


class ModelResolutionContext(BaseModel):
    agent_name: str
    runtime_overrides: list[ModelSelection] = Field(default_factory=list)
    workflow_models: dict[str, ModelSelection] = Field(default_factory=dict)
    user_selection: ModelSelection | None = None
    orchestrator_override: ModelSelection | None = None
    agent_default: DefaultModelConfig | None = None
    override_rules: AgentOverrideRules | None = None


class AgentRunResult(BaseModel):
    output: dict[str, Any]
    tokens_estimated: int
    latency_ms: int
    model_used: ModelSelection
