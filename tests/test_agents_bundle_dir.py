import pytest

from src.config import (
    get_agents_bundle_dir,
    get_agents_custom_dir,
    get_agents_default_dir,
    get_agents_instructions_dir,
    get_agents_skills_dir,
)


def test_default_bundle_paths():
    bundle = get_agents_bundle_dir()
    assert get_agents_default_dir() == bundle / "default"
    assert get_agents_custom_dir() == bundle / "custom"
    assert get_agents_skills_dir() == bundle / "skills"
    assert get_agents_instructions_dir() == bundle / "instructions"


def test_loaders_use_custom_bundle_dir(tmp_path, monkeypatch):
    bundle = tmp_path / "external-bundle"
    (bundle / "default").mkdir(parents=True)
    (bundle / "custom").mkdir()
    (bundle / "skills").mkdir()
    (bundle / "instructions").mkdir()

    (bundle / "default" / "backend.md").write_text(
        """# Backend Agent

## DEFAULT_MODEL
- provider: openai
- model: gpt-4o-mini
- temperature: 0.2

## ROLE
Backend externo
""",
        encoding="utf-8",
    )
    (bundle / "skills" / "code-standards.md").write_text(
        """---
name: code-standards
description: Test skill
---

Standards from external bundle.
""",
        encoding="utf-8",
    )
    (bundle / "instructions" / "global-rules.md").write_text(
        """---
name: global-rules
description: Test rules
---

Rules from external bundle.
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("AGENTS_BUNDLE_DIR", str(bundle))
    from src.settings import get_settings

    get_settings.cache_clear()

    from src.agents.loader import AgentLoader
    from src.instructions.loader import InstructionLoader
    from src.skills.loader import SkillLoader

    agent = AgentLoader().load("backend")
    assert "Backend externo" in agent.role

    skill = SkillLoader().load("code-standards")
    assert "external bundle" in skill.content

    instructions = InstructionLoader().load_all()
    assert any("external bundle" in i.content for i in instructions)

    get_settings.cache_clear()
