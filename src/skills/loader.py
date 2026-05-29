import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from src.config import get_agents_skills_dir


@dataclass
class SkillDefinition:
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    content: str = ""


def _parse_frontmatter(content: str) -> tuple[dict[str, str | list[str]], str]:
    if not content.startswith("---"):
        return {}, content
    match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)", content)
    if not match:
        return {}, content
    frontmatter_raw, body = match.group(1), match.group(2)
    meta: dict[str, str | list[str]] = {}
    for line in frontmatter_raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [x.strip().strip("'\"") for x in value[1:-1].split(",") if x.strip()]
        else:
            meta[key] = value.strip("'\"")
    return meta, body.strip()


class SkillLoader:
    def load(self, skill_name: str) -> SkillDefinition:
        path = get_agents_skills_dir() / f"{skill_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Skill não encontrada: {skill_name}")
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        return SkillDefinition(
            name=str(meta.get("name", skill_name)),
            description=str(meta.get("description", "")),
            tags=list(tags),
            content=body,
        )

    def load_many(self, skill_names: list[str], *, capabilities: list[str] | None = None) -> list[SkillDefinition]:
        loaded: list[SkillDefinition] = []
        for name in skill_names:
            try:
                skill = self.load(name)
            except FileNotFoundError:
                continue
            if capabilities and skill.tags:
                if not any(cap in skill.tags or cap in skill.name for cap in capabilities):
                    continue
            loaded.append(skill)
        return loaded

    def list_skills(self) -> list[str]:
        skills_dir = get_agents_skills_dir()
        if not skills_dir.exists():
            return []
        return sorted(
            p.stem for p in skills_dir.glob("*.md")
            if not p.stem.startswith("_")
        )

    def compose_prompt_block(self, skills: list[SkillDefinition]) -> str:
        if not skills:
            return ""
        parts = ["--- SKILLS ---"]
        for skill in skills:
            parts.append(f"\n### Skill: {skill.name}")
            if skill.description:
                parts.append(f"*{skill.description}*")
            parts.append(skill.content)
        return "\n".join(parts)


@lru_cache
def get_skill_loader() -> SkillLoader:
    return SkillLoader()
