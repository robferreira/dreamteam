from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.agents.repository import CustomAgentService
from src.api.schemas.tasks import AgentCreateRequest, AgentResponse, AgentUpdateRequest
from src.config import get_agents_custom_dir
from src.memory.postgres import get_custom_agent_repository
from src.schemas.models import AgentDefinition

router = APIRouter()
_service = CustomAgentService()


def _agent_source(agent_id: str, definition: AgentDefinition) -> str:
    if not definition.is_custom:
        return "default"
    if (get_agents_custom_dir() / f"{agent_id}.md").exists():
        return "file"
    return "db"


def _definition_to_response(agent_id: str, definition: AgentDefinition) -> AgentResponse:
    return AgentResponse(
        id=agent_id,
        slug=agent_id,
        name=definition.name,
        role=definition.role,
        default_provider=definition.default_model.provider,
        default_model=definition.default_model.model,
        tools=definition.tools,
        permissions=definition.permissions,
        restrictions=definition.restrictions,
        visibility=definition.visibility if definition.is_custom else "public",
        is_custom=definition.is_custom,
        source=_agent_source(agent_id, definition),
    )


@router.post("/create", response_model=AgentResponse)
async def create_agent(request: AgentCreateRequest):
    try:
        agent = await _service.create(
            name=request.name,
            role=request.role,
            prompt_md=request.prompt_md,
            provider=request.model.provider,
            model=request.model.model,
            temperature=request.model.temperature or 0.2,
            tools=request.tools,
            permissions=request.permissions,
            restrictions=request.restrictions,
            context=request.context,
            owner_id=request.owner_id,
            visibility=request.visibility,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    row = await get_custom_agent_repository().get_by_slug(agent.name)
    return AgentResponse(
        id=str(row.id),
        slug=row.slug,
        name=row.name,
        role=row.role,
        default_provider=row.default_provider,
        default_model=row.default_model,
        tools=row.tools or [],
        permissions=row.permissions or [],
        restrictions=row.restrictions or {},
        visibility=row.visibility,
        is_custom=True,
        source="db",
    )


@router.post("/update", response_model=AgentResponse)
async def update_agent(request: AgentUpdateRequest):
    updates: dict = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.role is not None:
        updates["role"] = request.role
    if request.prompt_md is not None:
        updates["prompt_md"] = request.prompt_md
    if request.model is not None:
        updates["default_provider"] = request.model.provider
        updates["default_model"] = request.model.model
        if request.model.temperature is not None:
            updates["default_temperature"] = request.model.temperature
    if request.tools is not None:
        updates["tools"] = request.tools
    if request.permissions is not None:
        updates["permissions"] = request.permissions
    if request.restrictions is not None:
        updates["restrictions"] = request.restrictions
    if request.context is not None:
        updates["context"] = request.context
    if request.visibility is not None:
        updates["visibility"] = request.visibility

    row = await _service.update(request.id, updates)
    if not row:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    db_row = await get_custom_agent_repository().get_by_id(request.id)
    return AgentResponse(
        id=str(db_row.id),
        slug=db_row.slug,
        name=db_row.name,
        role=db_row.role,
        default_provider=db_row.default_provider,
        default_model=db_row.default_model,
        tools=db_row.tools or [],
        permissions=db_row.permissions or [],
        restrictions=db_row.restrictions or {},
        visibility=db_row.visibility,
        is_custom=True,
        source="db",
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    from src.agents.loader import get_agent_loader

    loader = get_agent_loader()

    if agent_id in loader.list_system_agents() or agent_id in loader.list_custom_agents():
        definition = loader.load(agent_id)
        return _definition_to_response(agent_id, definition)

    repo = get_custom_agent_repository()
    try:
        uid = UUID(agent_id)
        row = await repo.get_by_id(uid)
    except ValueError:
        row = await repo.get_by_slug(agent_id)

    if not row:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    definition = loader._from_custom_db(row)
    return AgentResponse(
        id=str(row.id),
        slug=row.slug,
        name=row.name,
        role=row.role,
        default_provider=row.default_provider,
        default_model=row.default_model,
        tools=row.tools or [],
        permissions=row.permissions or [],
        restrictions=row.restrictions or {},
        visibility=row.visibility,
        is_custom=True,
        source=_agent_source(row.slug, definition),
    )
