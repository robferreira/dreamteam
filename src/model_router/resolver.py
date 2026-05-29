from src.schemas.models import (
    DefaultModelConfig,
    ModelResolutionContext,
    ModelSelection,
    ModelSource,
)
from src.settings import load_system_defaults


class ModelResolver:
    """Cascata de prioridade para resolução de modelo."""

    def resolve(self, ctx: ModelResolutionContext) -> ModelSelection | None:
        agent = ctx.agent_name

        if ctx.orchestrator_override and ctx.orchestrator_override.agent == agent:
            sel = ctx.orchestrator_override.model_copy()
            sel.source = ModelSource.ORCHESTRATOR_OVERRIDE
            return sel

        if ctx.user_selection and ctx.user_selection.agent == agent:
            sel = ctx.user_selection.model_copy()
            sel.source = ModelSource.USER_API
            return sel

        if agent in ctx.workflow_models:
            sel = ctx.workflow_models[agent].model_copy()
            sel.source = ModelSource.WORKFLOW
            return sel

        for override in ctx.runtime_overrides:
            if override.agent == agent:
                sel = override.model_copy()
                sel.source = ModelSource.RUNTIME
                return sel

        if ctx.agent_default:
            return ModelSelection(
                agent=agent,
                provider=ctx.agent_default.provider,
                model=ctx.agent_default.model,
                temperature=ctx.agent_default.temperature,
                max_tokens=ctx.agent_default.max_tokens,
                source=ModelSource.AGENT_DEFAULT,
            )

        system = load_system_defaults().get("default_model", {})
        if system:
            return ModelSelection(
                agent=agent,
                provider=system.get("provider", "openai"),
                model=system.get("model", "gpt-4o-mini"),
                temperature=system.get("temperature", 0.2),
                max_tokens=system.get("max_tokens"),
                source=ModelSource.SYSTEM_DEFAULT,
            )

        return None
