import pytest

from plugins.base import PluginContext
from plugins.builtin.scaffold_validator import scaffold_validator


@pytest.mark.asyncio
async def test_frontend_missing_package_json_warns():
    ctx = PluginContext(
        agent_name="frontend",
        output={
            "artifacts": [
                {"type": "code", "path": "frontend/src/App.tsx", "content": "...", "description": "x"}
            ]
        },
    )
    result = await scaffold_validator(ctx)
    assert result.errors
    assert any("package.json" in e for e in result.errors)
    assert "plugin_warnings" in result.output


@pytest.mark.asyncio
async def test_frontend_complete_scaffold_ok():
    ctx = PluginContext(
        agent_name="frontend",
        output={
            "artifacts": [
                {"type": "code", "path": "frontend/package.json", "content": "{}", "description": "x"},
                {"type": "code", "path": "frontend/index.html", "content": "<html></html>", "description": "x"},
                {"type": "code", "path": "frontend/src/main.tsx", "content": "...", "description": "x"},
                {"type": "code", "path": "frontend/src/App.tsx", "content": "...", "description": "x"},
            ]
        },
    )
    result = await scaffold_validator(ctx)
    assert not result.errors


@pytest.mark.asyncio
async def test_backend_python_without_entry_warns():
    ctx = PluginContext(
        agent_name="backend",
        output={
            "artifacts": [
                {"type": "code", "path": "src/utils/helpers.py", "content": "...", "description": "x"}
            ]
        },
    )
    result = await scaffold_validator(ctx)
    assert result.errors
    assert any("scaffold backend" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_scaffold_validator_registered():
    from plugins.registry import get_plugin_registry

    registry = get_plugin_registry()
    assert "scaffold_validator" in registry.list_plugins()
