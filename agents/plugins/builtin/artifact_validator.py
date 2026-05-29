from plugins.base import PluginContext, PluginResult

REQUIRED_FIELDS = ("type", "path", "content")
SPECIALIST_AGENTS = {"backend", "frontend", "database", "devops", "security", "documentation"}


async def artifact_validator(ctx: PluginContext) -> PluginResult:
    """Exige campos obrigatórios em artifacts de specialists."""
    output = dict(ctx.output)
    errors: list[str] = []
    artifacts = output.get("artifacts", [])
    if ctx.agent_name not in SPECIALIST_AGENTS or not isinstance(artifacts, list):
        return PluginResult(output=output)

    valid = []
    for i, item in enumerate(artifacts):
        if not isinstance(item, dict):
            errors.append(f"artifacts[{i}]: deve ser objeto")
            continue
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        if missing:
            errors.append(f"artifacts[{i}]: campos obrigatórios ausentes: {', '.join(missing)}")
            continue
        if not str(item["content"]).strip():
            errors.append(f"artifacts[{i}]: content vazio em {item.get('path')}")
            continue
        valid.append(item)

    output["artifacts"] = valid
    if errors:
        output.setdefault("plugin_warnings", []).extend(errors)
    return PluginResult(output=output, errors=errors, modified=len(valid) != len(artifacts))
