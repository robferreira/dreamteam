from unittest.mock import patch

import pytest

from src.model_router.router import ModelRouter
from src.schemas.models import (
    DefaultModelConfig,
    ModelResolutionContext,
    ModelSelection,
    ModelSource,
)


@pytest.fixture
def router():
    return ModelRouter()


def test_fallback_anthropic_to_openai_when_key_missing(router):
    ctx = ModelResolutionContext(
        agent_name="backend",
        workflow_models={
            "backend": ModelSelection(
                agent="backend",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                source=ModelSource.WORKFLOW,
            )
        },
        agent_default=DefaultModelConfig(provider="openai", model="gpt-4o-mini"),
    )
    with patch("src.llm.provider_availability.get_settings") as mock_settings:
        mock_settings.return_value.openai_api_key = "sk-test"
        mock_settings.return_value.anthropic_api_key = ""
        mock_settings.return_value.google_api_key = ""
        result = router.resolve(ctx)

    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"


def test_no_fallback_when_provider_configured(router):
    ctx = ModelResolutionContext(
        agent_name="backend",
        workflow_models={
            "backend": ModelSelection(
                agent="backend",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                source=ModelSource.WORKFLOW,
            )
        },
    )
    with patch("src.llm.provider_availability.get_settings") as mock_settings:
        mock_settings.return_value.openai_api_key = "sk-test"
        mock_settings.return_value.anthropic_api_key = "sk-ant-test"
        mock_settings.return_value.google_api_key = ""
        result = router.resolve(ctx)

    assert result.provider == "anthropic"
    assert result.model == "claude-3-5-sonnet-20241022"
