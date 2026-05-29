import re
from typing import Any
from uuid import UUID

from src.memory.postgres import get_custom_agent_repository
from src.schemas.models import AgentDefinition


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "agent"


class CustomAgentService:
    def __init__(self) -> None:
        self._repo = get_custom_agent_repository()

    async def create(
        self,
        name: str,
        role: str,
        prompt_md: str,
        provider: str,
        model: str,
        temperature: float = 0.2,
        tools: list[str] | None = None,
        permissions: list[str] | None = None,
        restrictions: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        owner_id: str | None = None,
        visibility: str = "private",
    ) -> AgentDefinition:
        from src.agents.loader import AgentLoader
        from src.config import get_agents_custom_dir, get_agents_default_dir

        slug = _slugify(name)
        if (get_agents_default_dir() / f"{slug}.md").exists():
            raise ValueError(f"Slug '{slug}' conflita com agente de sistema")
        if (get_agents_custom_dir() / f"{slug}.md").exists():
            raise ValueError(f"Agente com slug '{slug}' já existe em agents/custom/")
        existing = await self._repo.get_by_slug(slug)
        if existing:
            raise ValueError(f"Agente com slug '{slug}' já existe")

        row = await self._repo.create(
            {
                "slug": slug,
                "name": name,
                "role": role,
                "prompt_md": prompt_md,
                "default_provider": provider,
                "default_model": model,
                "default_temperature": temperature,
                "tools": tools or [],
                "permissions": permissions or [],
                "restrictions": restrictions or {},
                "context": context or {},
                "owner_id": owner_id,
                "visibility": visibility,
            }
        )
        from src.agents.loader import AgentLoader

        return AgentLoader()._from_custom_db(row)

    async def update(self, agent_id: UUID, updates: dict[str, Any]) -> AgentDefinition | None:
        row = await self._repo.update(agent_id, updates)
        if not row:
            return None
        from src.agents.loader import AgentLoader

        return AgentLoader()._from_custom_db(row)

    async def get(self, agent_id: UUID) -> AgentDefinition | None:
        row = await self._repo.get_by_id(agent_id)
        if not row:
            return None
        from src.agents.loader import AgentLoader

        return AgentLoader()._from_custom_db(row)

    async def get_by_slug(self, slug: str) -> AgentDefinition | None:
        row = await self._repo.get_by_slug(slug)
        if not row:
            return None
        from src.agents.loader import AgentLoader

        return AgentLoader()._from_custom_db(row)
