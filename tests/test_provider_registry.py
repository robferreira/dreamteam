from unittest.mock import patch, MagicMock

from src.llm.registry import ProviderRegistry
from src.schemas.models import ModelSelection


def test_registry_has_all_providers():
    registry = ProviderRegistry()
    for name in ["openai", "anthropic", "google", "ollama", "vllm"]:
        provider = registry.get(name)
        assert provider.name == name


def test_openai_create():
    registry = ProviderRegistry()
    with patch("src.llm.providers.openai.ChatOpenAI", return_value=MagicMock()) as mock:
        selection = ModelSelection(agent="x", provider="openai", model="gpt-4o-mini")
        registry.create(selection)
        mock.assert_called_once()
