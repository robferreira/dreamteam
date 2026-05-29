from src.agents.output_schemas import has_high_severity_issues
from src.graph.routing import _review_blocks_progress, route_next


def test_review_blocks_progress_on_high():
    review = {
        "approved": True,
        "issues": [{"severity": "high", "description": "security flaw", "agent": "backend"}],
    }
    assert _review_blocks_progress(review)
    assert has_high_severity_issues(review)


def test_review_blocks_progress_when_not_approved():
    review = {"approved": False, "issues": []}
    assert _review_blocks_progress(review)


def test_review_allows_when_approved_no_high():
    review = {
        "approved": True,
        "issues": [{"severity": "low", "description": "naming", "agent": "backend"}],
    }
    assert not _review_blocks_progress(review)


def test_route_blocks_memory_on_high_issues():
    state = {
        "iteration_count": 10,
        "workflow_config": {
            "required_agents": ["requirements", "planner", "reviewer", "memory"],
            "specialists": ["backend"],
            "max_revisions": 2,
        },
        "workflow_type": "bugfix",
        "specification": {"functional_requirements": []},
        "task_plan": {"tasks": [{"agent": "backend"}]},
        "artifacts": {"backend": {"artifacts": []}},
        "specialists_pending": ["backend"],
        "specialists_done": ["backend"],
        "review_result": {
            "approved": True,
            "issues": [{"severity": "high", "description": "bug", "agent": "backend"}],
            "refactor_requests": [{"agent": "backend", "reason": "fix bug"}],
        },
        "revision_count": 0,
        "visited_agents": ["reviewer"],
    }
    next_agent = route_next(state)
    assert next_agent in ("reviewer", "backend")
    assert next_agent != "memory"
