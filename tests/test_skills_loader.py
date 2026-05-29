import pytest

from src.skills.loader import get_skill_loader


def test_list_skills():
    loader = get_skill_loader()
    skills = loader.list_skills()
    assert "code-standards" in skills
    assert "api-design" in skills
    assert "reviewer-checklist" in skills


def test_load_skill():
    loader = get_skill_loader()
    skill = loader.load("code-standards")
    assert skill.name == "code-standards"
    assert skill.description
    assert "type hints" in skill.content.lower() or "Python" in skill.content


def test_load_many_skills():
    loader = get_skill_loader()
    skills = loader.load_many(["code-standards", "api-design"])
    assert len(skills) == 2


def test_compose_prompt_block():
    loader = get_skill_loader()
    skills = loader.load_many(["code-standards"])
    block = loader.compose_prompt_block(skills)
    assert "--- SKILLS ---" in block
    assert "code-standards" in block


def test_load_missing_skill_raises():
    loader = get_skill_loader()
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent-skill")
