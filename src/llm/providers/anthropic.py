from langchain_core.language_models.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic

from src.schemas.models import ModelSelection
from src.settings import get_settings, load_providers_config


class AnthropicProvider:
    name = "anthropic"

    def supports_model(self, model: str) -> bool:
        models = load_providers_config().get("providers", {}).get("anthropic", {}).get("models", [])
        return not models or model in models

    def create(self, selection: ModelSelection) -> BaseChatModel:
        settings = get_settings()
        return ChatAnthropic(
            model=selection.model,
            temperature=selection.temperature or 0.2,
            max_tokens=selection.max_tokens or 4096,
            api_key=settings.anthropic_api_key or None,
            timeout=settings.request_timeout_seconds,
        )
