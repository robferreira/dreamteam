import pytest

from src.model_router.router import ModelRouter
from src.model_router.validator import ModelValidationError
from src.schemas.models import (
    AgentOverrideRules,
    DefaultModelConfig,
    ModelResolutionContext,
    ModelSelection,
    ModelSource,
)


@pytest.fixture
def router():
    return ModelRouter()


def test_priority_orchestrator_override(router):
    ctx = ModelResolutionContext(
        agent_name="backend",
        orchestrator_override=ModelSelection(
            agent="backend", provider="anthropic", model="claude-3-5-sonnet-20241022"
        ),
        user_selection=ModelSelection(agent="backend", provider="openai", model="gpt-4o"),
        agent_default=DefaultModelConfig(provider="openai", model="gpt-4.1"),
    )
    result = router.resolve(ctx)
    assert result.provider == "anthropic"
    assert result.source == ModelSource.ORCHESTRATOR_OVERRIDE


def test_priority_user_api(router):
    ctx = ModelResolutionContext(
        agent_name="backend",
        user_selection=ModelSelection(
            agent="backend", provider="openai", model="gpt-4o", source=ModelSource.USER_API
        ),
        agent_default=DefaultModelConfig(provider="openai", model="gpt-4.1"),
    )
    result = router.resolve(ctx)
    assert result.model == "gpt-4o"
    assert result.source == ModelSource.USER_API


def test_priority_workflow(router):
    ctx = ModelResolutionContext(
        agent_name="planner",
        workflow_models={
            "planner": ModelSelection(
                agent="planner", provider="openai", model="gpt-4.1", source=ModelSource.WORKFLOW
            )
        },
        agent_default=DefaultModelConfig(provider="openai", model="gpt-4o-mini"),
    )
    result = router.resolve(ctx)
    assert result.model == "gpt-4.1"
    assert result.source == ModelSource.WORKFLOW


def test_fallback_agent_default(router):
    ctx = ModelResolutionContext(
        agent_name="backend",
        agent_default=DefaultModelConfig(provider="openai", model="gpt-4.1"),
    )
    result = router.resolve(ctx)
    assert result.model == "gpt-4.1"
    assert result.source == ModelSource.AGENT_DEFAULT


def test_no_model_raises(router):
    from unittest.mock import patch

    ctx = ModelResolutionContext(agent_name="unknown")
    with patch("src.model_router.resolver.load_system_defaults", return_value={}):
        with pytest.raises(ModelValidationError):
            router.resolve(ctx)


def test_override_rules_provider_blocked(router):
    ctx = ModelResolutionContext(
        agent_name="backend",
        agent_default=DefaultModelConfig(provider="google", model="gemini-1.5-pro"),
        override_rules=AgentOverrideRules(allow_providers=["openai"], max_cost_tier="standard"),
    )
    with pytest.raises(ModelValidationError):
        router.resolve(ctx)
