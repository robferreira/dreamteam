from src.schemas.models import AgentOverrideRules, ModelSelection
from src.settings import get_settings, load_providers_config


class ModelValidationError(ValueError):
    pass


class ModelValidator:
    def validate(
        self,
        selection: ModelSelection,
        override_rules: AgentOverrideRules | None = None,
    ) -> None:
        settings = get_settings()
        providers = load_providers_config().get("providers", {})
        provider = selection.provider.lower()

        if provider not in providers and not settings.allow_unknown_models:
            raise ModelValidationError(f"Provider não permitido: {provider}")

        if provider in providers:
            cfg = providers[provider]
            allowed_models = cfg.get("models") or []
            if (
                allowed_models
                and selection.model not in allowed_models
                and not settings.allow_unknown_models
            ):
                raise ModelValidationError(
                    f"Modelo '{selection.model}' não permitido para provider '{provider}'"
                )

        if override_rules and override_rules.allow_providers:
            if provider not in [p.lower() for p in override_rules.allow_providers]:
                raise ModelValidationError(
                    f"Provider '{provider}' não permitido pelas regras do agente"
                )
