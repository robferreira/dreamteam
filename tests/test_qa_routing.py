from src.graph.routing import QA_AGENT, route_next


def _base_state(**overrides):
    state = {
        "iteration_count": 5,
        "workflow_config": {
            "required_agents": ["requirements", "planner", "qa", "reviewer", "memory"],
            "specialists": ["backend"],
            "max_revisions": 2,
        },
        "workflow_type": "bugfix",
        "specification": {"functional_requirements": []},
        "task_plan": {"tasks": [{"agent": "backend"}]},
        "artifacts": {"backend": {"artifacts": []}},
        "specialists_pending": ["backend"],
        "specialists_done": ["backend"],
        "active_agents": ["requirements", "planner", "backend", "qa", "reviewer", "memory"],
    }
    state.update(overrides)
    return state


def test_route_qa_after_specialists():
    state = _base_state()
    assert route_next(state) == QA_AGENT


def test_route_reviewer_after_qa():
    state = _base_state(
        qa_result={
            "e2e_passed": True,
            "execution": [{"suite": "api", "passed": True, "total": 1, "failed": 0}],
        },
        visited_agents=["qa"],
    )
    assert route_next(state) == "reviewer"


def test_route_qa_rerun_after_backend_refactor():
    state = _base_state(
        qa_result={"e2e_passed": False, "execution": [{"suite": "api", "passed": False}]},
        visited_agents=["qa", "backend"],
    )
    assert route_next(state) == QA_AGENT


def test_route_skips_qa_when_not_in_team():
    state = _base_state(active_agents=["requirements", "planner", "backend", "reviewer", "memory"])
    assert route_next(state) == "reviewer"
