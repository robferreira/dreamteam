import re
from dataclasses import dataclass
from functools import lru_cache

from src.config import get_agents_instructions_dir


@dataclass
class InstructionDefinition:
    name: str
    description: str = ""
    content: str = ""


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---"):
        return {}, content
    match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)", content)
    if not match:
        return {}, content
    frontmatter_raw, body = match.group(1), match.group(2)
    meta: dict[str, str] = {}
    for line in frontmatter_raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip("'\"")
    return meta, body.strip()


class InstructionLoader:
    def load(self, instruction_name: str) -> InstructionDefinition:
        path = get_agents_instructions_dir() / f"{instruction_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Instruction não encontrada: {instruction_name}")
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        return InstructionDefinition(
            name=str(meta.get("name", instruction_name)),
            description=str(meta.get("description", "")),
            content=body,
        )

    def load_all(self) -> list[InstructionDefinition]:
        instructions_dir = get_agents_instructions_dir()
        if not instructions_dir.exists():
            return []
        loaded: list[InstructionDefinition] = []
        for path in sorted(instructions_dir.glob("*.md")):
            if path.stem.startswith("_"):
                continue
            loaded.append(self.load(path.stem))
        return loaded

    def list_instructions(self) -> list[str]:
        instructions_dir = get_agents_instructions_dir()
        if not instructions_dir.exists():
            return []
        return sorted(
            p.stem for p in instructions_dir.glob("*.md")
            if not p.stem.startswith("_")
        )

    def compose_prompt_block(self, instructions: list[InstructionDefinition] | None = None) -> str:
        items = instructions if instructions is not None else self.load_all()
        if not items:
            return ""
        parts = ["--- INSTRUCTIONS GLOBAIS ---"]
        for instruction in items:
            parts.append(f"\n### {instruction.name}")
            if instruction.description:
                parts.append(f"*{instruction.description}*")
            parts.append(instruction.content)
        return "\n".join(parts)


@lru_cache
def get_instruction_loader() -> InstructionLoader:
    return InstructionLoader()
