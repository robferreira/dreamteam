import re
from typing import Any

from src.schemas.models import AgentDefinition, AgentOverrideRules, DefaultModelConfig


def _parse_yaml_list_block(text: str) -> list[str]:
    items = []
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            val = line[2:].strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                items.extend([x.strip().strip("'\"") for x in inner.split(",") if x.strip()])
            else:
                items.append(val)
    return items


def _parse_key_value_block(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            line = line[2:]
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                result[key] = [x.strip().strip("'\"") for x in value[1:-1].split(",") if x.strip()]
            else:
                try:
                    result[key] = float(value) if "." in value else int(value)
                except ValueError:
                    result[key] = value.strip("'\"")
    return result


def _extract_section(content: str, section: str) -> str:
    pattern = rf"##\s*{re.escape(section)}\s*\n([\s\S]*?)(?=\n##\s|\Z)"
    match = re.search(pattern, content, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_agent_markdown(name: str, content: str) -> AgentDefinition:
    role_section = _extract_section(content, "ROLE") or _extract_section(content, "Role")
    role = role_section.split("\n")[0].strip("# ").strip() if role_section else name

    default_block = _extract_section(content, "DEFAULT_MODEL")
    if not default_block:
        raise ValueError(f"Agente '{name}' deve conter seção ## DEFAULT_MODEL")
    default_kv = _parse_key_value_block(default_block)
    default_model = DefaultModelConfig(
        provider=str(default_kv.get("provider", "openai")),
        model=str(default_kv.get("model", "gpt-4o-mini")),
        temperature=float(default_kv.get("temperature", 0.2)),
        max_tokens=default_kv.get("max_tokens"),
    )

    override_block = _extract_section(content, "OVERRIDE_RULES")
    override_rules = AgentOverrideRules()
    if override_block:
        override_kv = _parse_key_value_block(override_block)
        allow = override_kv.get("allow_providers", [])
        if isinstance(allow, str):
            allow = [allow]
        override_rules = AgentOverrideRules(
            allow_providers=allow if isinstance(allow, list) else _parse_yaml_list_block(override_block),
            max_cost_tier=str(override_kv.get("max_cost_tier", "standard")),
        )

    capabilities_block = _extract_section(content, "CAPABILITIES")
    capabilities = _parse_yaml_list_block(capabilities_block) if capabilities_block else []

    skills_block = _extract_section(content, "SKILLS")
    skills = _parse_yaml_list_block(skills_block) if skills_block else []

    plugins_block = _extract_section(content, "PLUGINS")
    plugins = _parse_yaml_list_block(plugins_block) if plugins_block else []

    constraints_block = _extract_section(content, "CONSTRAINTS")
    constraints = _parse_yaml_list_block(constraints_block) if constraints_block else []

    acceptance_block = _extract_section(content, "ACCEPTANCE_CRITERIA")
    acceptance_criteria = _parse_yaml_list_block(acceptance_block) if acceptance_block else []

    reject_block = _extract_section(content, "REJECT_IF")
    reject_if = _parse_yaml_list_block(reject_block) if reject_block else []

    output_schema_block = _extract_section(content, "OUTPUT_SCHEMA_REF")
    output_schema_ref = output_schema_block.split("\n")[0].strip("- ").strip() if output_schema_block else ""

    return AgentDefinition(
        name=name,
        role=role,
        capabilities=capabilities,
        default_model=default_model,
        override_rules=override_rules,
        raw_prompt=content,
        is_custom=False,
        skills=skills,
        plugins=plugins,
        constraints=constraints,
        acceptance_criteria=acceptance_criteria,
        reject_if=reject_if,
        output_schema_ref=output_schema_ref,
    )
