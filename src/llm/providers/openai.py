from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.schemas.models import ModelSelection
from src.settings import get_settings, load_providers_config


class OpenAIProvider:
    name = "openai"

    def supports_model(self, model: str) -> bool:
        models = load_providers_config().get("providers", {}).get("openai", {}).get("models", [])
        return not models or model in models

    def create(self, selection: ModelSelection) -> BaseChatModel:
        settings = get_settings()
        return ChatOpenAI(
            model=selection.model,
            temperature=selection.temperature or 0.2,
            max_tokens=selection.max_tokens,
            api_key=settings.openai_api_key or None,
            timeout=settings.request_timeout_seconds,
        )
