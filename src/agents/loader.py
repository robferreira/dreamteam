from functools import lru_cache
from pathlib import Path

from src.agents.parser import parse_agent_markdown
from src.config import get_agents_custom_dir, get_agents_default_dir
from src.memory.postgres import get_custom_agent_repository
from src.schemas.models import AgentDefinition, AgentOverrideRules, DefaultModelConfig


class AgentLoader:
    def _custom_path(self, agent_name: str) -> Path:
        return get_agents_custom_dir() / f"{agent_name}.md"

    def _default_path(self, agent_name: str) -> Path:
        return get_agents_default_dir() / f"{agent_name}.md"

    def _load_from_file(self, agent_name: str, path: Path, *, is_custom: bool) -> AgentDefinition:
        content = path.read_text(encoding="utf-8")
        definition = parse_agent_markdown(agent_name, content)
        definition.is_custom = is_custom
        return definition

    def load(self, agent_name: str) -> AgentDefinition:
        if agent_name.startswith("_"):
            raise FileNotFoundError(f"Agente não encontrado: {agent_name}")

        custom_path = self._custom_path(agent_name)
        if custom_path.exists():
            return self._load_from_file(agent_name, custom_path, is_custom=True)

        default_path = self._default_path(agent_name)
        if default_path.exists():
            return self._load_from_file(agent_name, default_path, is_custom=False)

        return self._load_custom_sync(agent_name)

    async def load_async(self, agent_name: str) -> AgentDefinition:
        if agent_name.startswith("_"):
            raise FileNotFoundError(f"Agente não encontrado: {agent_name}")

        custom_path = self._custom_path(agent_name)
        if custom_path.exists():
            return self._load_from_file(agent_name, custom_path, is_custom=True)

        default_path = self._default_path(agent_name)
        if default_path.exists():
            return self._load_from_file(agent_name, default_path, is_custom=False)

        repo = get_custom_agent_repository()
        custom = await repo.get_by_slug(agent_name)
        if custom:
            return self._from_custom_db(custom)
        raise FileNotFoundError(f"Agente não encontrado: {agent_name}")

    def _load_custom_sync(self, agent_name: str) -> AgentDefinition:
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.load_async(agent_name))
        raise FileNotFoundError(
            f"Agente custom '{agent_name}' requer load_async em contexto async"
        )

    def _from_custom_db(self, custom) -> AgentDefinition:
        restrictions = custom.restrictions or {}
        definition = parse_agent_markdown(custom.slug, custom.prompt_md) if custom.prompt_md else None
        if definition:
            definition.is_custom = True
            definition.tools = custom.tools or definition.tools
            definition.permissions = custom.permissions or []
            definition.restrictions = restrictions
            definition.context = custom.context or {}
            definition.owner_id = custom.owner_id
            definition.visibility = custom.visibility
            return definition
        return AgentDefinition(
            name=custom.slug,
            role=custom.role,
            capabilities=[],
            default_model=DefaultModelConfig(
                provider=custom.default_provider,
                model=custom.default_model,
                temperature=custom.default_temperature,
            ),
            override_rules=AgentOverrideRules(
                allow_providers=restrictions.get("allow_providers", []),
                max_cost_tier=restrictions.get("max_cost_tier", "standard"),
            ),
            raw_prompt=custom.prompt_md,
            is_custom=True,
            plugins=list(custom.tools or []),
            tools=custom.tools or [],
            permissions=custom.permissions or [],
            restrictions=restrictions,
            context=custom.context or {},
            owner_id=custom.owner_id,
            visibility=custom.visibility,
        )

    def list_system_agents(self) -> list[str]:
        default_dir = get_agents_default_dir()
        if not default_dir.exists():
            return []
        return sorted(
            p.stem for p in default_dir.glob("*.md")
            if not p.stem.startswith("_")
        )

    def list_custom_agents(self) -> list[str]:
        custom_dir = get_agents_custom_dir()
        if not custom_dir.exists():
            return []
        return sorted(
            p.stem for p in custom_dir.glob("*.md")
            if not p.stem.startswith("_")
        )

    def list_all_agents(self) -> list[str]:
        return sorted(set(self.list_system_agents()) | set(self.list_custom_agents()))


@lru_cache
def get_agent_loader() -> AgentLoader:
    return AgentLoader()
