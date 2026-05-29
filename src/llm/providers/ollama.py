from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from src.schemas.models import ModelSelection
from src.settings import get_settings


class OllamaProvider:
    name = "ollama"

    def supports_model(self, model: str) -> bool:
        return True

    def create(self, selection: ModelSelection) -> BaseChatModel:
        settings = get_settings()
        return ChatOllama(
            model=selection.model,
            temperature=selection.temperature or 0.2,
            base_url=settings.ollama_base_url,
        )
