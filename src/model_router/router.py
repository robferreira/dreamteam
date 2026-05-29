from functools import lru_cache

from src.llm.provider_availability import apply_provider_fallback
from src.model_router.cost_policy import CostPolicy
from src.model_router.resolver import ModelResolver
from src.model_router.validator import ModelValidationError, ModelValidator
from src.schemas.models import ModelResolutionContext, ModelSelection


class ModelRouter:
    def __init__(self) -> None:
        self._resolver = ModelResolver()
        self._validator = ModelValidator()
        self._cost_policy = CostPolicy()

    def resolve(
        self,
        ctx: ModelResolutionContext,
        *,
        force_economy: bool = False,
    ) -> ModelSelection:
        selection = self._resolver.resolve(ctx)
        if selection is None:
            raise ModelValidationError(
                f"Nenhum modelo resolvido para agente '{ctx.agent_name}'"
            )

        selection = apply_provider_fallback(selection)
        selection = self._cost_policy.apply_economy_override(selection, force_economy)
        self._validator.validate(selection, ctx.override_rules)
        self._cost_policy.validate_tier(selection, ctx.override_rules)
        return selection


@lru_cache
def get_model_router() -> ModelRouter:
    return ModelRouter()
