from functools import lru_cache
from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel

from src.llm.providers.anthropic import AnthropicProvider
from src.llm.providers.google import GoogleProvider
from src.llm.providers.ollama import OllamaProvider
from src.llm.providers.openai import OpenAIProvider
from src.llm.providers.vllm import VLLMProvider
from src.schemas.models import ModelSelection


class LLMProvider(Protocol):
    name: str

    def create(self, selection: ModelSelection) -> BaseChatModel: ...
    def supports_model(self, model: str) -> bool: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self.register(OpenAIProvider())
        self.register(AnthropicProvider())
        self.register(GoogleProvider())
        self.register(OllamaProvider())
        self.register(VLLMProvider())

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.name.lower()] = provider

    def get(self, name: str) -> LLMProvider:
        key = name.lower()
        if key not in self._providers:
            raise ValueError(f"Provedor LLM desconhecido: {name}")
        return self._providers[key]

    def create(self, selection: ModelSelection) -> BaseChatModel:
        provider = self.get(selection.provider)
        return provider.create(selection)


@lru_cache
def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry()
