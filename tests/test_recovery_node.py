from unittest.mock import AsyncMock, patch

import pytest

from src.graph.nodes.agents import recovery_node


@pytest.mark.asyncio
async def test_recovery_node_retries_frontend_without_pending_provision():
    state = {
        "demand": "test",
        "iteration_count": 1,
        "recovery_attempts": 0,
        "failure_context": {
            "kind": "provision",
            "target": "frontend",
            "error": "npm ci failed",
            "failure_kind": "install_failed",
        },
        "provision_result": [{"target": "frontend", "success": False}],
    }

    with patch("src.graph.nodes.agents._execute_agent", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "action": "retry_agent",
            "target_agent": "frontend",
            "rationale": "Corrigir package.json",
            "fix_instructions": "Adicionar @vitejs/plugin-react",
            "retry_provision": True,
            "abort": False,
        }
        result = await recovery_node(state)

    assert result["recovery_attempts"] == 1
    assert result.get("recovery_override") == "frontend"
    assert not result.get("pending_retry_provision")
    assert not result.get("force_stop")
    assert result.get("failure_context") == {}
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_recovery_node_tool_not_found_deterministic_retry():
    state = {
        "demand": "test",
        "iteration_count": 1,
        "recovery_attempts": 0,
        "failure_context": {
            "kind": "provision",
            "target": "frontend",
            "error": "[WinError 193] %1 não é um aplicativo Win32 válido",
            "failure_kind": "tool_not_found",
        },
    }

    with patch("src.graph.nodes.agents._execute_agent", new_callable=AsyncMock) as mock_exec:
        result = await recovery_node(state)

    mock_exec.assert_not_called()
    assert result["recovery_attempts"] == 0
    assert result.get("pending_retry_provision") is True
    assert result.get("pending_provision_target") == "frontend"
    assert not result.get("force_stop")
    assert result.get("recovery_result", {}).get("action") == "retry_provision"


@pytest.mark.asyncio
async def test_recovery_node_aborts_after_max_attempts():
    state = {
        "demand": "test",
        "iteration_count": 1,
        "recovery_attempts": 2,
        "failure_context": {"kind": "provision", "error": "irrecoverable"},
    }

    with patch("src.graph.nodes.agents._execute_agent", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "action": "retry_agent",
            "target_agent": "frontend",
            "abort": False,
        }
        with patch("src.graph.nodes.agents.load_global_settings") as mock_settings:
            mock_settings.return_value = {"max_recovery_attempts": 3}
            result = await recovery_node(state)

    assert result["recovery_attempts"] == 3
    assert result.get("force_stop") is True


@pytest.mark.asyncio
async def test_recovery_node_respects_abort_flag():
    state = {
        "demand": "test",
        "iteration_count": 1,
        "recovery_attempts": 0,
        "failure_context": {"kind": "qa", "error": "e2e fail"},
    }

    with patch("src.graph.nodes.agents._execute_agent", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "action": "abort",
            "abort": True,
            "rationale": "Sem Node no host",
        }
        result = await recovery_node(state)

    assert result.get("force_stop") is True
    assert "Node" in result.get("error", "")
