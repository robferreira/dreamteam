from src.schemas.models import AgentOverrideRules, ModelSelection
from src.settings import load_cost_tiers, load_providers_config


class CostPolicy:
    """Aplica tier de custo e pode sugerir downgrade de modelo."""

    def get_provider_tier(self, provider: str) -> str:
        providers = load_providers_config().get("providers", {})
        cfg = providers.get(provider.lower(), {})
        return cfg.get("cost_tier", "standard")

    def validate_tier(
        self,
        selection: ModelSelection,
        override_rules: AgentOverrideRules | None = None,
    ) -> None:
        if not override_rules:
            return
        max_tier = override_rules.max_cost_tier
        tiers = load_cost_tiers().get("tiers", {})
        tier_order = ["economy", "standard", "premium"]
        provider_tier = self.get_provider_tier(selection.provider)

        if max_tier in tier_order and provider_tier in tier_order:
            if tier_order.index(provider_tier) > tier_order.index(max_tier):
                allowed = tiers.get(max_tier, {}).get("allowed_providers", [])
                if allowed and selection.provider.lower() not in [p.lower() for p in allowed]:
                    from src.model_router.validator import ModelValidationError

                    raise ModelValidationError(
                        f"Provider '{selection.provider}' excede max_cost_tier '{max_tier}'"
                    )

    def apply_economy_override(
        self,
        selection: ModelSelection,
        force_economy: bool = False,
    ) -> ModelSelection:
        if not force_economy:
            return selection
        tier = self.get_provider_tier(selection.provider)
        if tier != "economy":
            return ModelSelection(
                agent=selection.agent,
                provider="ollama",
                model="llama3.2",
                temperature=selection.temperature or 0.2,
                source=selection.source,
            )
        return selection
