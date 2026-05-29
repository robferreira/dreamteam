import pytest

from plugins.base import PluginContext
from plugins.builtin.artifact_validator import artifact_validator
from plugins.builtin.path_guard import path_guard
from plugins.builtin.review_gate import review_gate
from plugins.registry import get_plugin_registry


@pytest.mark.asyncio
async def test_path_guard_rejects_absolute_paths():
    ctx = PluginContext(
        agent_name="backend",
        output={
            "artifacts": [
                {"type": "code", "path": "/etc/passwd", "content": "x", "description": "bad"},
                {"type": "code", "path": "src/main.py", "content": "ok", "description": "good"},
            ]
        },
    )
    result = await path_guard(ctx)
    assert len(result.output["artifacts"]) == 1
    assert result.output["artifacts"][0]["path"] == "src/main.py"
    assert result.errors


@pytest.mark.asyncio
async def test_artifact_validator_requires_fields():
    ctx = PluginContext(
        agent_name="backend",
        output={
            "artifacts": [
                {"path": "src/main.py"},
                {"type": "code", "path": "src/app.py", "content": "print('hi')", "description": "app"},
            ]
        },
    )
    result = await artifact_validator(ctx)
    assert len(result.output["artifacts"]) == 1
    assert result.errors


@pytest.mark.asyncio
async def test_review_gate_forces_rejection_on_high():
    ctx = PluginContext(
        agent_name="reviewer",
        output={
            "approved": True,
            "issues": [{"severity": "high", "description": "SQL injection", "agent": "backend"}],
            "refactor_requests": [],
        },
    )
    result = await review_gate(ctx)
    assert result.output["approved"] is False
    assert result.modified
    assert result.output["refactor_requests"]


@pytest.mark.asyncio
async def test_plugin_registry_pipeline():
    registry = get_plugin_registry()
    output, errors = await registry.run_pipeline(
        ["path_guard", "artifact_validator"],
        agent_name="backend",
        output={
            "artifacts": [
                {"type": "code", "path": "src/main.py", "content": "x=1", "description": "main"},
            ]
        },
    )
    assert output["artifacts"]
    assert "path_guard" in registry.list_plugins()
