from src.logging_config import get_logger
from src.schemas.models import ModelSelection, ModelSource
from src.settings import get_settings, load_system_defaults

logger = get_logger(__name__)

_FALLBACK_ORDER = ("openai", "anthropic", "google", "ollama", "vllm")


def is_provider_configured(provider: str) -> bool:
    key = provider.lower()
    settings = get_settings()
    if key == "openai":
        return bool(settings.openai_api_key)
    if key == "anthropic":
        return bool(settings.anthropic_api_key)
    if key == "google":
        return bool(settings.google_api_key)
    if key in ("ollama", "vllm"):
        return True
    return False


def _default_fallback_selection(agent: str, provider: str) -> ModelSelection:
    defaults = load_system_defaults().get("default_model", {})
    return ModelSelection(
        agent=agent,
        provider=provider,
        model=defaults.get("model", "gpt-4o-mini"),
        temperature=defaults.get("temperature", 0.2),
        max_tokens=defaults.get("max_tokens"),
        source=ModelSource.SYSTEM_DEFAULT,
    )


def apply_provider_fallback(selection: ModelSelection) -> ModelSelection:
    if is_provider_configured(selection.provider):
        return selection

    original_provider = selection.provider
    for provider in _FALLBACK_ORDER:
        if not is_provider_configured(provider):
            continue
        fallback = selection.model_copy(
            update={
                "provider": provider,
                "source": ModelSource.SYSTEM_DEFAULT,
            }
        )
        if provider == "openai":
            defaults = load_system_defaults().get("default_model", {})
            fallback.model = defaults.get("model", "gpt-4o-mini")
        logger.warning(
            "provider_fallback_applied",
            agent=selection.agent,
            from_provider=original_provider,
            to_provider=provider,
            to_model=fallback.model,
        )
        return fallback

    return _default_fallback_selection(selection.agent, "openai")
