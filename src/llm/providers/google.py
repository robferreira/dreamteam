from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from src.schemas.models import ModelSelection
from src.settings import get_settings, load_providers_config


class GoogleProvider:
    name = "google"

    def supports_model(self, model: str) -> bool:
        models = load_providers_config().get("providers", {}).get("google", {}).get("models", [])
        return not models or model in models

    def create(self, selection: ModelSelection) -> BaseChatModel:
        settings = get_settings()
        return ChatGoogleGenerativeAI(
            model=selection.model,
            temperature=selection.temperature or 0.2,
            max_output_tokens=selection.max_tokens,
            google_api_key=settings.google_api_key or None,
            timeout=settings.request_timeout_seconds,
        )
