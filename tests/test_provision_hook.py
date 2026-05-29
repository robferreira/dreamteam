from unittest.mock import AsyncMock, patch

import pytest

from src.graph.nodes.agents import make_agent_node
from src.projects.provision_hook import provision_after_specialist


@pytest.mark.asyncio
async def test_frontend_node_triggers_provision():
    node = make_agent_node("frontend", "artifacts")
    state = {
        "demand": "test",
        "project_path": "projects/test",
        "iteration_count": 0,
        "artifacts": {},
        "files_written_count": 0,
        "architecture": {"stack": "react"},
    }

    with patch("src.graph.nodes.agents._execute_agent", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"artifacts": [], "notes": ""}
        with patch("src.graph.nodes.agents._write_artifacts", new_callable=AsyncMock) as mock_write:
            mock_write.return_value = 1
            with patch(
                "src.graph.nodes.agents.provision_after_specialist",
                new_callable=AsyncMock,
            ) as mock_prov:
                mock_prov.return_value = {
                    "provision_result": [{"target": "frontend", "success": True, "steps": []}],
                }
                result = await node(state)

    mock_prov.assert_called_once()
    assert result.get("provision_result")


@pytest.mark.asyncio
async def test_frontend_node_sets_failure_context_on_provision_failure():
    node = make_agent_node("frontend", "artifacts")
    state = {
        "demand": "test",
        "project_path": "projects/test",
        "iteration_count": 0,
        "artifacts": {},
        "files_written_count": 0,
    }

    with patch("src.graph.nodes.agents._execute_agent", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"artifacts": []}
        with patch("src.graph.nodes.agents._write_artifacts", new_callable=AsyncMock) as mock_write:
            mock_write.return_value = 1
            with patch(
                "src.graph.nodes.agents.provision_after_specialist",
                new_callable=AsyncMock,
            ) as mock_prov:
                mock_prov.return_value = {
                    "failure_context": {
                        "kind": "provision",
                        "target": "frontend",
                        "error": "Node.js não encontrado",
                    },
                    "provision_result": [{"target": "frontend", "success": False}],
                }
                result = await node(state)

    assert result.get("failure_context", {}).get("kind") == "provision"
    assert not result.get("force_stop")
    assert "Node.js" in result.get("failure_context", {}).get("error", "")


@pytest.mark.asyncio
async def test_provision_hook_sets_failure_context_not_force_stop(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    state = {"project_path": str(tmp_path), "architecture": {"stack": "react"}}

    with patch("src.projects.provision_hook.ProjectProvisioner") as mock_cls:
        mock_inst = mock_cls.return_value
        from src.projects.provisioner import ProvisionResult

        mock_inst.provision_frontend.return_value = ProvisionResult(
            target="frontend",
            success=False,
            error="npm não encontrado",
            failure_kind="tool_not_found",
        )
        patch_result = await provision_after_specialist(state, "frontend")

    assert patch_result is not None
    assert patch_result.get("failure_context", {}).get("kind") == "provision"
    assert "force_stop" not in patch_result
