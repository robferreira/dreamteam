import pytest

from plugins.base import PluginContext
from plugins.builtin.qa_gate import qa_gate


@pytest.mark.asyncio
async def test_qa_gate_forces_rejection_on_e2e_failure():
    ctx = PluginContext(
        agent_name="reviewer",
        output={"approved": True, "issues": [], "refactor_requests": []},
        extra={
            "qa_result": {
                "e2e_passed": False,
                "execution": [
                    {
                        "suite": "api",
                        "passed": False,
                        "failed": 2,
                        "failures": [{"message": "assert 500 == 200", "agent": "backend"}],
                    }
                ],
            }
        },
    )
    result = await qa_gate(ctx)
    assert result.output["approved"] is False
    assert result.modified
    assert result.output["refactor_requests"]
    assert any(i.get("severity") == "high" for i in result.output["issues"])


@pytest.mark.asyncio
async def test_qa_gate_ignores_when_e2e_passed():
    ctx = PluginContext(
        agent_name="reviewer",
        output={"approved": True, "issues": []},
        extra={"qa_result": {"e2e_passed": True, "execution": []}},
    )
    result = await qa_gate(ctx)
    assert result.output["approved"] is True
    assert not result.modified


@pytest.mark.asyncio
async def test_qa_gate_ignores_non_reviewer():
    ctx = PluginContext(
        agent_name="backend",
        output={},
        extra={"qa_result": {"e2e_passed": False}},
    )
    result = await qa_gate(ctx)
    assert result.output == {}
