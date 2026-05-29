import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.models import (
    AgentOverrideRules,
    DefaultModelConfig,
    ModelResolutionContext,
    ModelSelection,
    ModelSource,
)


@pytest.fixture
def sample_model_selection():
    return ModelSelection(
        agent="backend",
        provider="openai",
        model="gpt-4o-mini",
        temperature=0.2,
        source=ModelSource.USER_API,
    )


@pytest.fixture
def sample_agent_default():
    return DefaultModelConfig(provider="openai", model="gpt-4.1", temperature=0.2)


@pytest.fixture
def mock_llm_response():
    mock = MagicMock()
    mock.content = '{"status": "ok", "approved": true}'
    return mock


@pytest.fixture
def patch_run_agent(mock_llm_response):
    from src.schemas.models import AgentRunResult

    async def fake_run_agent(*args, **kwargs):
        return AgentRunResult(
            output={"status": "ok", "approved": True},
            tokens_estimated=100,
            latency_ms=50,
            model_used=ModelSelection(
                agent=kwargs.get("agent_name", "backend"),
                provider="openai",
                model="gpt-4o-mini",
                source=ModelSource.AGENT_DEFAULT,
            ),
        )

    with patch("src.agents.runner.run_agent", new=AsyncMock(side_effect=fake_run_agent)):
        yield
