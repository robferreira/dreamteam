from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.schemas.models import ModelSelection
from src.settings import get_settings


class VLLMProvider:
    name = "vllm"

    def supports_model(self, model: str) -> bool:
        return True

    def create(self, selection: ModelSelection) -> BaseChatModel:
        settings = get_settings()
        return ChatOpenAI(
            model=selection.model,
            temperature=selection.temperature or 0.2,
            max_tokens=selection.max_tokens,
            api_key="EMPTY",
            base_url=settings.vllm_base_url,
            timeout=settings.request_timeout_seconds,
        )
