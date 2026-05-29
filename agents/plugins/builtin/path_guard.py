from plugins.base import PluginContext, PluginResult


async def path_guard(ctx: PluginContext) -> PluginResult:
    """Rejeita artifacts com paths absolutos ou suspeitos."""
    output = dict(ctx.output)
    errors: list[str] = []
    artifacts = output.get("artifacts", [])
    if not isinstance(artifacts, list):
        return PluginResult(output=output)

    cleaned = []
    for item in artifacts:
        if not isinstance(item, dict):
            errors.append(f"Artifact inválido (não é objeto): {item}")
            continue
        path = str(item.get("path", ""))
        if not path:
            errors.append("Artifact sem path")
            continue
        if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
            errors.append(f"Path absoluto não permitido: {path}")
            continue
        if ".." in path.split("/"):
            errors.append(f"Path traversal não permitido: {path}")
            continue
        cleaned.append(item)

    output["artifacts"] = cleaned
    if errors:
        output.setdefault("plugin_warnings", []).extend(errors)
    return PluginResult(output=output, errors=errors, modified=bool(errors))
