from src.agents.parser import parse_agent_markdown

SAMPLE_MD = """# Backend Agent

## DEFAULT_MODEL
- provider: openai
- model: gpt-4.1
- temperature: 0.3

## OVERRIDE_RULES
- allow_providers: [openai, anthropic]
- max_cost_tier: standard

## CAPABILITIES
- code_generation
- api_design

## SKILLS
- code-standards
- api-design

## PLUGINS
- path_guard
- artifact_validator

## CONSTRAINTS
- Type hints obrigatórios
- Paths relativos

## ACCEPTANCE_CRITERIA
- Artifacts completos

## REJECT_IF
- JSON inválido

## ROLE
Desenvolvedor backend senior
"""


def test_parse_default_model():
    defn = parse_agent_markdown("backend", SAMPLE_MD)
    assert defn.default_model.provider == "openai"
    assert defn.default_model.model == "gpt-4.1"
    assert defn.default_model.temperature == 0.3


def test_parse_override_rules():
    defn = parse_agent_markdown("backend", SAMPLE_MD)
    assert "openai" in defn.override_rules.allow_providers
    assert defn.override_rules.max_cost_tier == "standard"


def test_parse_capabilities():
    defn = parse_agent_markdown("backend", SAMPLE_MD)
    assert "code_generation" in defn.capabilities


def test_parse_role():
    defn = parse_agent_markdown("backend", SAMPLE_MD)
    assert "backend" in defn.role.lower()


def test_parse_skills_and_plugins():
    defn = parse_agent_markdown("backend", SAMPLE_MD)
    assert "code-standards" in defn.skills
    assert "api-design" in defn.skills
    assert "path_guard" in defn.plugins
    assert "artifact_validator" in defn.plugins


def test_parse_constraints_and_criteria():
    defn = parse_agent_markdown("backend", SAMPLE_MD)
    assert any("Type hints" in c for c in defn.constraints)
    assert any("Artifacts" in a for a in defn.acceptance_criteria)
    assert any("JSON" in r for r in defn.reject_if)


def test_effective_plugins_merges_tools():
    from src.schemas.models import AgentDefinition, DefaultModelConfig

    defn = AgentDefinition(
        name="custom",
        default_model=DefaultModelConfig(provider="openai", model="gpt-4o-mini"),
        plugins=["path_guard"],
        tools=["artifact_validator"],
    )
    assert defn.effective_plugins == ["path_guard", "artifact_validator"]


def test_system_agents_have_default_model():
    from src.agents.loader import get_agent_loader

    loader = get_agent_loader()
    for name in loader.list_system_agents():
        defn = loader.load(name)
        assert defn.default_model.provider
        assert defn.default_model.model


def test_template_not_in_system_agents():
    from src.agents.loader import get_agent_loader

    loader = get_agent_loader()
    assert "_template" not in loader.list_system_agents()
