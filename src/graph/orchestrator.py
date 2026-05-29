from langgraph.graph import END, StateGraph

from src.graph.checkpoint import get_checkpointer
from src.graph.nodes.agents import (
    cost_optimizer_node,
    finalize_node,
    make_agent_node,
    memory_node,
    monitoring_node,
    orchestrator_node,
    specialists_parallel_node,
)
from src.graph.state import AgentState

AGENT_NODES = [
    "requirements",
    "architect",
    "planner",
    "backend",
    "frontend",
    "database",
    "devops",
    "security",
    "documentation",
    "reviewer",
]

OUTPUT_KEYS = {
    "requirements": "specification",
    "architect": "architecture",
    "planner": "task_plan",
    "reviewer": "review_result",
}


def _route_from_orchestrator(state: AgentState) -> str:
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "FINISH" or state.get("force_stop"):
        return "finalize"
    return next_agent


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("monitoring", monitoring_node)
    graph.add_node("cost_optimizer", cost_optimizer_node)
    graph.add_node("memory", memory_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("specialists_parallel", specialists_parallel_node)

    for agent in AGENT_NODES:
        output_key = OUTPUT_KEYS.get(agent, "artifacts")
        graph.add_node(agent, make_agent_node(agent, output_key))

    graph.set_entry_point("orchestrator")

    route_map = {agent: agent for agent in AGENT_NODES}
    route_map["monitoring"] = "monitoring"
    route_map["cost_optimizer"] = "cost_optimizer"
    route_map["memory"] = "memory"
    route_map["finalize"] = "finalize"
    route_map["specialists_parallel"] = "specialists_parallel"

    graph.add_conditional_edges("orchestrator", _route_from_orchestrator, route_map)

    for agent in AGENT_NODES:
        graph.add_edge(agent, "orchestrator")

    graph.add_edge("specialists_parallel", "orchestrator")
    graph.add_edge("monitoring", "orchestrator")
    graph.add_edge("cost_optimizer", "orchestrator")
    graph.add_edge("memory", "orchestrator")
    graph.add_edge("finalize", END)

    return graph


_compiled_graph = None


async def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        checkpointer = await get_checkpointer()
        _compiled_graph = build_graph().compile(checkpointer=checkpointer)
    return _compiled_graph
