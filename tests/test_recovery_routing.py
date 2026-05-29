from src.graph.routing import PROVISION_RETRY, QA_AGENT, RECOVERY_AGENT, route_next


def _base_state(**overrides):
    state = {
        "iteration_count": 5,
        "workflow_config": {
            "required_agents": ["requirements", "planner", "qa", "reviewer", "memory"],
            "specialists": ["frontend"],
            "max_revisions": 2,
        },
        "workflow_type": "new-feature",
        "specification": {"functional_requirements": []},
        "task_plan": {"tasks": [{"agent": "frontend"}]},
        "artifacts": {"frontend": {"artifacts": []}},
        "specialists_pending": ["frontend"],
        "specialists_done": ["frontend"],
        "active_agents": ["frontend", "qa", "reviewer", "recovery"],
        "recovery_attempts": 0,
    }
    state.update(overrides)
    return state


def test_route_to_recovery_on_failure_context():
    state = _base_state(
        failure_context={
            "kind": "provision",
            "target": "frontend",
            "error": "npm failed",
            "recoverable": True,
        },
    )
    assert route_next(state) == RECOVERY_AGENT


def test_route_to_provision_retry_when_pending():
    state = _base_state(
        pending_retry_provision=True,
        pending_provision_target="frontend",
    )
    assert route_next(state) == PROVISION_RETRY


def test_recovery_override_before_provision_retry():
    state = _base_state(
        recovery_override="frontend",
        pending_retry_provision=True,
        pending_provision_target="frontend",
        failure_context={},
    )
    assert route_next(state) == "frontend"


def test_route_to_recovery_override_agent():
    state = _base_state(
        recovery_override="frontend",
        failure_context={},
    )
    assert route_next(state) == "frontend"


def test_route_to_qa_when_pending_retry_qa():
    state = _base_state(
        pending_retry_qa=True,
        qa_result={"e2e_passed": False},
    )
    assert route_next(state) == QA_AGENT


def test_recovery_skipped_when_max_attempts_exhausted():
    state = _base_state(
        failure_context={"kind": "provision", "error": "fail"},
        recovery_attempts=3,
    )
    assert route_next(state) != RECOVERY_AGENT


def test_force_stop_finishes():
    state = _base_state(force_stop=True)
    assert route_next(state) == "FINISH"
