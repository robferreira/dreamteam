import pytest

from src.agents.loader import get_agent_loader


def test_load_default_agent():
    loader = get_agent_loader()
    definition = loader.load("backend")
    assert definition.name == "backend"
    assert definition.is_custom is False


def test_list_system_agents_from_default_dir():
    loader = get_agent_loader()
    agents = loader.list_system_agents()
    assert "backend" in agents
    assert "architect" in agents
    assert "_template" not in agents


def test_list_custom_agents_empty_by_default():
    loader = get_agent_loader()
    custom = loader.list_custom_agents()
    assert isinstance(custom, list)


def test_list_all_agents_includes_default():
    loader = get_agent_loader()
    all_agents = loader.list_all_agents()
    assert "backend" in all_agents
    assert len(all_agents) >= len(loader.list_system_agents())


def test_custom_file_takes_priority_over_default(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    custom_dir = bundle / "custom"
    default_dir = bundle / "default"
    custom_dir.mkdir(parents=True)
    default_dir.mkdir(parents=True)

    default_content = """# Backend Agent

## DEFAULT_MODEL
- provider: openai
- model: gpt-4o-mini
- temperature: 0.2

## ROLE
Default backend
"""
    custom_content = """# Backend Agent

## DEFAULT_MODEL
- provider: openai
- model: gpt-4o-mini
- temperature: 0.2

## ROLE
Custom backend override
"""
    (default_dir / "backend.md").write_text(default_content, encoding="utf-8")
    (custom_dir / "backend.md").write_text(custom_content, encoding="utf-8")

    monkeypatch.setenv("AGENTS_BUNDLE_DIR", str(bundle))
    from src.settings import get_settings

    get_settings.cache_clear()

    from src.agents.loader import AgentLoader

    loader = AgentLoader()
    definition = loader.load("backend")
    assert definition.is_custom is True
    assert "Custom backend" in definition.role

    get_settings.cache_clear()


def test_custom_file_marked_as_custom(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    custom_dir = bundle / "custom"
    default_dir = bundle / "default"
    custom_dir.mkdir(parents=True)
    default_dir.mkdir(parents=True)

    content = """# Meu Agente

## DEFAULT_MODEL
- provider: openai
- model: gpt-4o-mini
- temperature: 0.2

## ROLE
Meu agente custom
"""
    (custom_dir / "meuagente.md").write_text(content, encoding="utf-8")

    monkeypatch.setenv("AGENTS_BUNDLE_DIR", str(bundle))
    from src.settings import get_settings

    get_settings.cache_clear()

    from src.agents.loader import AgentLoader

    loader = AgentLoader()
    definition = loader.load("meuagente")
    assert definition.is_custom is True
    assert "meuagente" in loader.list_custom_agents()

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_missing_agent_raises(monkeypatch):
    class MockRepo:
        async def get_by_slug(self, slug: str):
            return None

    monkeypatch.setattr(
        "src.agents.loader.get_custom_agent_repository",
        lambda: MockRepo(),
    )

    loader = get_agent_loader()
    with pytest.raises(FileNotFoundError):
        await loader.load_async("agente-inexistente-xyz")
