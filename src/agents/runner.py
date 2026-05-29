import json
import re
import time
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.loader import get_agent_loader
from src.agents.output_schemas import validate_agent_output
from src.llm.registry import get_provider_registry
from src.logging_config import get_logger
from src.memory.postgres import get_task_repository
from src.memory.rag import retrieve_context
from src.model_router.router import get_model_router
from src.instructions.loader import get_instruction_loader
from src.orchestrator.prompt_builder import PromptBuilder
from src.config import ensure_plugins_path

ensure_plugins_path()

from plugins.registry import get_plugin_registry
from src.schemas.models import AgentRunResult, ModelResolutionContext, ModelSelection
from src.skills.loader import get_skill_loader

logger = get_logger(__name__)

MAX_VALIDATION_RETRIES = 2
SPECIALIST_AGENTS = {"backend", "frontend", "database", "devops", "security", "documentation"}


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"raw_response": text, "parse_error": True}


def build_model_context(
    agent_name: str,
    *,
    workflow_models: dict[str, ModelSelection] | None = None,
    user_models: list[ModelSelection] | None = None,
    runtime_overrides: list[ModelSelection] | None = None,
    orchestrator_override: ModelSelection | None = None,
    force_economy: bool = False,
) -> tuple[ModelResolutionContext, ModelSelection]:
    loader = get_agent_loader()
    try:
        definition = loader.load(agent_name)
    except FileNotFoundError:
        raise

    user_selection = None
    if user_models:
        for m in user_models:
            if m.agent == agent_name:
                user_selection = m
                break

    ctx = ModelResolutionContext(
        agent_name=agent_name,
        runtime_overrides=runtime_overrides or [],
        workflow_models=workflow_models or {},
        user_selection=user_selection,
        orchestrator_override=orchestrator_override,
        agent_default=definition.default_model,
        override_rules=definition.override_rules,
    )

    router = get_model_router()
    selection = router.resolve(ctx, force_economy=force_economy)
    return ctx, selection


async def run_agent(
    agent_name: str,
    user_message: str,
    *,
    workflow_models: dict[str, ModelSelection] | None = None,
    user_models: list[ModelSelection] | None = None,
    runtime_overrides: list[ModelSelection] | None = None,
    orchestrator_override: ModelSelection | None = None,
    project_id: str = "default",
    task_id: UUID | None = None,
    rag_doc_types: list[str] | None = None,
    use_rag: bool = True,
    force_economy: bool = False,
    extra_context: str = "",
    project_path: str = "",
    plugin_extra: dict[str, Any] | None = None,
) -> AgentRunResult:
    """Executa agente obrigatoriamente via ModelRouter."""
    start = time.perf_counter()
    loader = get_agent_loader()

    try:
        definition = await loader.load_async(agent_name)
    except FileNotFoundError:
        definition = loader.load(agent_name)

    user_selection = None
    if user_models:
        for m in user_models:
            if m.agent == agent_name:
                user_selection = m
                break

    ctx = ModelResolutionContext(
        agent_name=agent_name,
        runtime_overrides=runtime_overrides or [],
        workflow_models=workflow_models or {},
        user_selection=user_selection,
        orchestrator_override=orchestrator_override,
        agent_default=definition.default_model,
        override_rules=definition.override_rules,
    )

    router = get_model_router()
    selection = router.resolve(ctx, force_economy=force_economy)

    if task_id:
        from src.cache.redis_client import get_redis_cache
        from src.settings import get_settings

        repo = get_task_repository()
        await repo.update_task(task_id, current_agent=agent_name)
        ttl = get_settings().request_timeout_seconds + 30
        await get_redis_cache().set_task_heartbeat(str(task_id), ttl=ttl)

    registry = get_provider_registry()
    llm = registry.create(selection)

    skill_loader = get_skill_loader()
    skills = skill_loader.load_many(definition.skills, capabilities=definition.capabilities)
    skills_context = skill_loader.compose_prompt_block(skills)

    instruction_loader = get_instruction_loader()
    instructions_context = instruction_loader.compose_prompt_block()

    rag_context = ""
    if use_rag:
        doc_types = list(rag_doc_types or [])
        if agent_name in SPECIALIST_AGENTS and "standards" not in doc_types:
            doc_types.append("standards")
        rag_context = await retrieve_context(
            user_message, project_id=project_id, doc_types=doc_types or None
        )

    system_content = PromptBuilder.build_system_prompt(
        definition.raw_prompt,
        rag_context=rag_context,
        extra_context=extra_context,
        instructions_context=instructions_context,
        skills_context=skills_context,
        constraints=definition.constraints,
        acceptance_criteria=definition.acceptance_criteria,
        reject_if=definition.reject_if,
    )

    current_message = user_message
    output: dict[str, Any] = {}
    validation_errors: list[str] = []
    content = ""

    for attempt in range(MAX_VALIDATION_RETRIES + 1):
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=current_message),
        ]
        response = await llm.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        output = _extract_json(content)
        output, validation_errors = validate_agent_output(agent_name, output)
        if not validation_errors:
            break
        if attempt < MAX_VALIDATION_RETRIES:
            current_message = PromptBuilder.build_validation_retry_message(
                user_message, validation_errors
            )
            logger.warning(
                "agent_validation_retry",
                agent=agent_name,
                attempt=attempt + 1,
                errors=validation_errors,
            )

    if validation_errors:
        output["validation_error"] = validation_errors

    plugin_registry = get_plugin_registry()
    output, plugin_errors = await plugin_registry.run_pipeline(
        definition.effective_plugins,
        agent_name=agent_name,
        output=output,
        project_path=project_path,
        extra=plugin_extra or {},
    )
    if plugin_errors:
        output.setdefault("plugin_warnings", []).extend(plugin_errors)

    latency_ms = int((time.perf_counter() - start) * 1000)
    tokens_estimated = (len(system_content) + len(user_message) + len(content)) // 4

    if task_id:
        repo = get_task_repository()
        await repo.add_step(
            task_id=task_id,
            agent=agent_name,
            model_provider=selection.provider,
            model_name=selection.model,
            model_source=selection.source.value,
            tokens_estimated=tokens_estimated,
            latency_ms=latency_ms,
            output=output,
        )
        await repo.log_model_usage(
            task_id=task_id,
            agent=agent_name,
            provider=selection.provider,
            model=selection.model,
            source=selection.source.value,
            tokens_estimated=tokens_estimated,
            latency_ms=latency_ms,
        )

    logger.info(
        "agent_executed",
        agent=agent_name,
        provider=selection.provider,
        model=selection.model,
        source=selection.source.value,
        latency_ms=latency_ms,
        validation_errors=bool(validation_errors),
    )

    return AgentRunResult(
        output=output,
        tokens_estimated=tokens_estimated,
        latency_ms=latency_ms,
        model_used=selection,
    )
