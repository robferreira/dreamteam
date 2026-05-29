"""Roteamento determinístico — LangGraph NÃO decide modelos."""

from src.agents.output_schemas import has_high_severity_issues
from src.graph.state import AgentState
from src.settings import load_global_settings

SPECIALISTS = ["backend", "frontend", "database", "devops", "security", "documentation"]
SUPPORT_AGENTS = ["monitoring", "cost_optimizer"]


def _agent_in_team(state: AgentState, agent: str) -> bool:
    active = state.get("active_agents")
    if not active:
        return True
    return agent in active


def _count_visits(state: AgentState, agent: str) -> int:
    return state.get("visited_agents", []).count(agent)


def _review_blocks_progress(review: dict) -> bool:
    """Bloqueia avanço se review não aprovado ou com issues high."""
    if not review:
        return False
    if has_high_severity_issues(review):
        return True
    return not review.get("approved", False)


def _should_stop(state: AgentState) -> bool:
    settings = load_global_settings()
    if state.get("force_stop"):
        return True
    if state.get("iteration_count", 0) >= settings.get("max_iterations", 20):
        return True
    return False


def get_specialists_for_plan(state: AgentState) -> list[str]:
    task_plan = state.get("task_plan") or {}
    tasks = task_plan.get("tasks", [])
    needed = {t.get("agent") for t in tasks if t.get("agent") in SPECIALISTS}
    if not needed:
        workflow = state.get("workflow_config") or {}
        needed = set(workflow.get("specialists", SPECIALISTS))
    return sorted(needed)


def route_next(state: AgentState) -> str:
    if _should_stop(state):
        return "FINISH"

    workflow = state.get("workflow_config") or {}
    max_revisions = workflow.get("max_revisions", 2)
    settings = load_global_settings()
    max_revisits = settings.get("max_agent_revisits", 3)

    visited = state.get("visited_agents", [])
    has_spec = bool(state.get("specification"))
    has_arch = bool(state.get("architecture"))
    has_plan = bool(state.get("task_plan"))
    has_artifacts = bool(state.get("artifacts"))
    review = state.get("review_result") or {}
    has_review = bool(review)
    has_memory = bool(state.get("memory_result"))
    workflow_name = state.get("workflow_type", "new-feature")

    if (
        "requirements" in workflow.get("required_agents", [])
        and not has_spec
        and _agent_in_team(state, "requirements")
    ):
        if _count_visits(state, "requirements") < max_revisits:
            return "requirements"

    needs_arch = state.get("needs_architecture", workflow.get("needs_architecture_default", False))
    spec = state.get("specification") or {}
    if spec.get("needs_architecture") is not None:
        needs_arch = spec["needs_architecture"]

    if needs_arch and not has_arch:
        agents_pool = workflow.get("optional_agents", []) + workflow.get("required_agents", [])
        if (
            "architect" in agents_pool
            and _agent_in_team(state, "architect")
            and _count_visits(state, "architect") < max_revisits
        ):
            return "architect"

    if not has_plan:
        if workflow_name == "refactor" or has_spec or has_arch:
            if _agent_in_team(state, "planner") and _count_visits(state, "planner") < max_revisits:
                return "planner"

    pending = state.get("specialists_pending") or get_specialists_for_plan(state)
    done = set(state.get("specialists_done") or [])
    active = state.get("active_agents") or []
    if active:
        pending = [s for s in pending if s in active]
    remaining = [s for s in pending if s not in done]

    if has_plan and len(remaining) > 1:
        return "specialists_parallel"
    if has_plan and remaining:
        return remaining[0]

    if has_artifacts or (has_plan and not remaining):
        review_blocks = has_review and _review_blocks_progress(review)
        if not has_review or (
            review_blocks
            and state.get("revision_count", 0) < max_revisions
            and (review.get("refactor_requests") or has_high_severity_issues(review))
        ):
            if _count_visits(state, "reviewer") < max_revisits + max_revisions:
                if has_review and review_blocks and review.get("refactor_requests"):
                    refactor_agent = review["refactor_requests"][0].get("agent")
                    if refactor_agent and refactor_agent in SPECIALISTS:
                        if _count_visits(state, refactor_agent) < max_revisits:
                            return refactor_agent
                if _agent_in_team(state, "reviewer") and (
                    not has_review or state.get("revision_count", 0) < max_revisions
                ):
                    return "reviewer"

    if has_review and review.get("approved") and not has_high_severity_issues(review):
        if "documentation" in (workflow.get("specialists") or []):
            if (
                _agent_in_team(state, "documentation")
                and "documentation" not in done
                and _count_visits(state, "documentation") < max_revisits
            ):
                return "documentation"

    if (
        has_review
        and review.get("approved")
        and not has_high_severity_issues(review)
    ) or state.get("revision_count", 0) >= max_revisions:
        if (
            not has_memory
            and "memory" in workflow.get("required_agents", [])
            and _agent_in_team(state, "memory")
        ):
            if _count_visits(state, "memory") < max_revisits:
                return "memory"

    if has_memory and _agent_in_team(state, "cost_optimizer") and _count_visits(state, "cost_optimizer") == 0:
        return "cost_optimizer"

    if has_memory and _count_visits(state, "cost_optimizer") > 0:
        return "FINISH"

    if state.get("iteration_count", 0) > 0 and state.get("iteration_count", 0) % 5 == 0:
        if "monitoring" not in visited[-2:] and _count_visits(state, "monitoring") < max_revisits:
            return "monitoring"

    return "FINISH"
