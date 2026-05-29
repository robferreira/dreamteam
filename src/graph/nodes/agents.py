import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from src.agents.runner import run_agent
from src.graph.routing import get_specialists_for_plan
from src.graph.state import AgentState, models_from_state, user_models_from_state
from src.orchestrator.prompt_builder import PromptBuilder
from src.projects.artifact_writer import ArtifactWriter
from src.projects.service import get_project_service
from src.schemas.models import ModelSelection, ModelSource


def _build_context(state: AgentState) -> str:
    snapshot = {
        "demand": state.get("demand", ""),
        "project_metadata": state.get("project_metadata"),
        "project_path": state.get("project_path"),
        "specification": state.get("specification"),
        "architecture": state.get("architecture"),
        "task_plan": state.get("task_plan"),
        "artifacts": state.get("artifacts"),
        "review_result": state.get("review_result"),
    }
    return PromptBuilder.build_agent_message(
        state.get("demand", ""),
        snapshot,
        state.get("current_agent", ""),
    )


def _get_task_id(state: AgentState) -> UUID | None:
    tid = state.get("task_id")
    if tid:
        return UUID(str(tid))
    return None


def _get_writer(state: AgentState) -> ArtifactWriter | None:
    project_path = state.get("project_path")
    if not project_path:
        return None
    return ArtifactWriter(Path(project_path))


def _orchestrator_override(state: AgentState, agent_name: str) -> ModelSelection | None:
    for raw in state.get("orchestrator_model_overrides") or []:
        cfg = ModelSelection(**raw) if isinstance(raw, dict) else raw
        if cfg.agent == agent_name:
            cfg.source = ModelSource.ORCHESTRATOR_OVERRIDE
            return cfg
    return None


async def _execute_agent(state: AgentState, agent_name: str) -> dict[str, Any]:
    project_ctx = PromptBuilder.build_project_context(state.get("project_metadata") or {})
    user_msg = f"Execute sua função como agente '{agent_name}'.\n\n{_build_context(state)}"
    result = await run_agent(
        agent_name=agent_name,
        user_message=user_msg,
        workflow_models=models_from_state(state),
        user_models=user_models_from_state(state),
        orchestrator_override=_orchestrator_override(state, agent_name),
        project_id=state.get("project_id", "default"),
        task_id=_get_task_id(state),
        force_economy=state.get("force_economy", False),
        extra_context=project_ctx,
        project_path=state.get("project_path", ""),
    )
    return result.output


async def _write_artifacts(state: AgentState, agent: str, output: dict) -> int:
    writer = _get_writer(state)
    task_id = _get_task_id(state)
    if not writer:
        return 0
    files = await writer.write_from_agent_output_async(agent, output, task_id=task_id)
    return len(files)


def make_agent_node(agent_name: str, output_key: str | None = None):
    async def node(state: AgentState) -> dict[str, Any]:
        output = await _execute_agent(state, agent_name)
        files_written = 0
        result: dict[str, Any] = {
            "current_agent": agent_name,
            "visited_agents": [agent_name],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
        key = output_key or agent_name
        if key == "artifacts":
            existing = dict(state.get("artifacts") or {})
            existing[agent_name] = output
            result["artifacts"] = existing
            files_written = await _write_artifacts(state, agent_name, output)
        else:
            result[key] = output
            if agent_name == "architect":
                writer = _get_writer(state)
                if writer:
                    writer.write_json_file("docs/architecture.json", output)
                    stack = output.get("stack", "")
                    structure = output.get("structure", {})
                    md = f"# Arquitetura\n\n**Stack:** {stack}\n\n```json\n{json.dumps(structure, ensure_ascii=False, indent=2)}\n```\n"
                    writer.write_markdown_file("docs/architecture.md", md)
                    files_written += 2
                    if stack and state.get("project_slug"):
                        await get_project_service().update_stack_resolved(
                            state["project_slug"], stack
                        )
            elif agent_name == "requirements":
                writer = _get_writer(state)
                if writer:
                    writer.write_json_file("docs/specification.json", output)
                    files_written += 1

        prev_count = state.get("files_written_count", 0)
        result["files_written_count"] = prev_count + files_written

        if agent_name == "requirements" and output.get("needs_architecture") is not None:
            result["needs_architecture"] = output["needs_architecture"]
        if agent_name == "planner":
            specialists = get_specialists_for_plan({**state, "task_plan": output})
            result["specialists_pending"] = specialists
        if agent_name in ("backend", "frontend", "database", "devops", "security", "documentation"):
            result["specialists_done"] = [agent_name]
        if agent_name == "reviewer" and not output.get("approved"):
            result["revision_count"] = state.get("revision_count", 0) + 1
        return result

    node.__name__ = f"{agent_name}_node"
    return node


async def orchestrator_node(state: AgentState) -> dict[str, Any]:
    from src.graph.routing import route_next

    next_agent = route_next(state)
    return {
        "current_agent": "orchestrator",
        "next_agent": next_agent,
        "visited_agents": ["orchestrator"],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def specialists_parallel_node(state: AgentState) -> dict[str, Any]:
    pending = state.get("specialists_pending") or get_specialists_for_plan(state)
    done = set(state.get("specialists_done") or [])
    remaining = [s for s in pending if s not in done]
    if not remaining:
        return {"visited_agents": ["specialists_parallel"]}

    async def run_one(name: str) -> tuple[str, dict, int]:
        out = await _execute_agent(state, name)
        count = await _write_artifacts(state, name, out)
        return name, out, count

    results = await asyncio.gather(*[run_one(s) for s in remaining])
    artifacts = dict(state.get("artifacts") or {})
    done_list = []
    total_files = 0
    for name, output, count in results:
        artifacts[name] = output
        done_list.append(name)
        total_files += count

    return {
        "current_agent": "specialists_parallel",
        "visited_agents": ["specialists_parallel"] + done_list,
        "artifacts": artifacts,
        "specialists_done": done_list,
        "files_written_count": state.get("files_written_count", 0) + total_files,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def monitoring_node(state: AgentState) -> dict[str, Any]:
    from src.settings import load_global_settings

    settings = load_global_settings()
    visited = state.get("visited_agents", [])
    agent_counts: dict[str, int] = {}
    for v in visited:
        agent_counts[v] = agent_counts.get(v, 0) + 1

    alerts = []
    force_stop = False
    for agent, count in agent_counts.items():
        if count > settings.get("max_agent_revisits", 3):
            alerts.append(f"Agente {agent} visitado {count} vezes")
            force_stop = True

    return {
        "current_agent": "monitoring",
        "visited_agents": ["monitoring"],
        "monitoring_result": {"alerts": alerts, "agent_counts": agent_counts},
        "force_stop": force_stop,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def cost_optimizer_node(state: AgentState) -> dict[str, Any]:
    return {
        "current_agent": "cost_optimizer",
        "visited_agents": ["cost_optimizer"],
        "cost_result": {"force_economy": True},
        "force_economy": True,
        "orchestrator_model_overrides": [
            {
                "agent": a,
                "provider": "ollama",
                "model": "llama3.2",
                "source": "orchestrator_override",
            }
            for a in ["documentation", "monitoring"]
        ],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def memory_node(state: AgentState) -> dict[str, Any]:
    output = await _execute_agent(state, "memory")
    if output.get("documents"):
        from src.memory.rag import index_document

        project_id = state.get("project_id", "default")
        for doc in output["documents"]:
            await index_document(
                project_id=project_id,
                doc_type=doc.get("type", "memory"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
            )
    return {
        "current_agent": "memory",
        "visited_agents": ["memory"],
        "memory_result": output,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def finalize_node(state: AgentState) -> dict[str, Any]:
    review = state.get("review_result") or {}
    project_slug = state.get("project_slug", "")
    project_path = state.get("project_path", "")
    root_path = f"projects/{project_slug}" if project_slug else ""

    manifest_data = None
    files_count = state.get("files_written_count", 0)
    writer = _get_writer(state)
    task_id = _get_task_id(state)
    if writer:
        manifest_data = await writer.write_all_artifacts(
            state.get("artifacts") or {},
            task_id=task_id,
        )
        writer.write_manifest(
            str(state.get("task_id", "")),
            state.get("workflow_type", ""),
            manifest_data,
        )
        files_count = len(manifest_data.written_files)

    final = {
        "approved": review.get("approved", False),
        "specification": state.get("specification"),
        "architecture": state.get("architecture"),
        "task_plan": state.get("task_plan"),
        "artifacts": state.get("artifacts"),
        "review_result": review,
        "memory_result": state.get("memory_result"),
        "visited_agents": state.get("visited_agents", []),
        "project_slug": project_slug,
        "project_path": root_path,
        "files_written_count": files_count,
        "manifest": {
            "written_files": [
                {"path": f.path, "agent": f.agent}
                for f in (manifest_data.written_files if manifest_data else [])
            ],
            "errors": manifest_data.errors if manifest_data else [],
        },
    }
    return {"final_result": final, "current_agent": "finalize"}
