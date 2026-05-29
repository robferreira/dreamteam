from src.skills.loader import get_skill_loader

BMAD_SKILLS = [
    "bmad-spec-driven",
    "bmad-requirements-pm",
    "bmad-architecture",
    "bmad-story-planning",
    "bmad-dev-discipline",
    "bmad-frontend-scaffold",
    "bmad-doc-accuracy",
    "bmad-code-review",
]


def test_bmad_skills_exist():
    loader = get_skill_loader()
    available = loader.list_skills()
    for name in BMAD_SKILLS:
        assert name in available, f"Skill BMAD ausente: {name}"


def test_bmad_skills_load_content():
    loader = get_skill_loader()
    skill = loader.load("bmad-spec-driven")
    assert "fonte da verdade" in skill.content.lower() or "spec" in skill.content.lower()


def test_requirements_agent_has_bmad_skills():
    from src.agents.loader import get_agent_loader

    defn = get_agent_loader().load("requirements")
    assert "bmad-spec-driven" in defn.skills
    assert "bmad-requirements-pm" in defn.skills


def test_frontend_agent_has_scaffold_plugin():
    from src.agents.loader import get_agent_loader

    defn = get_agent_loader().load("frontend")
    assert "scaffold_validator" in defn.plugins
    assert "bmad-frontend-scaffold" in defn.skills
