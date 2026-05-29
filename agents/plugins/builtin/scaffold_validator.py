from plugins.base import PluginContext, PluginResult

FRONTEND_MARKERS = (".tsx", ".jsx", ".vue")
FRONTEND_ENTRY_NAMES = ("main.tsx", "main.jsx", "index.tsx", "index.jsx")
FRONTEND_INDEX_HTML = "index.html"
PACKAGE_JSON = "package.json"

BACKEND_PYTHON_MARKERS = ("src/main.py", "main.py", "app.py")
BACKEND_DEPS = ("pyproject.toml", "requirements.txt", "Pipfile")


def _artifact_paths(output: dict) -> list[str]:
    artifacts = output.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []
    paths: list[str] = []
    for item in artifacts:
        if isinstance(item, dict) and item.get("path"):
            paths.append(str(item["path"]).replace("\\", "/").lower())
    return paths


def _has_frontend_scaffold(paths: list[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    has_ui = any(p.endswith(FRONTEND_MARKERS) for p in paths)
    if not has_ui:
        return True, errors

    has_package = any(p.endswith(PACKAGE_JSON) for p in paths)
    has_entry = any(p.split("/")[-1] in FRONTEND_ENTRY_NAMES for p in paths)
    has_html = any(p.endswith(FRONTEND_INDEX_HTML) for p in paths)

    if not has_package:
        errors.append("Scaffold frontend incompleto: falta package.json")
    if not has_entry:
        errors.append("Scaffold frontend incompleto: falta entry point (main.tsx/main.jsx/index.tsx)")
    if not has_html:
        errors.append("Scaffold frontend incompleto: falta index.html")

    return not errors, errors


def _has_backend_scaffold(paths: list[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    has_python = any(".py" in p for p in paths)
    if not has_python:
        return True, errors

    has_entry = any(p.endswith(BACKEND_PYTHON_MARKERS) for p in paths)
    has_deps = any(p.split("/")[-1] in BACKEND_DEPS for p in paths)

    if not has_entry and not has_deps:
        errors.append(
            "Scaffold backend incompleto: falta src/main.py (ou app.py) ou pyproject.toml/requirements.txt"
        )

    return not errors, errors


async def scaffold_validator(ctx: PluginContext) -> PluginResult:
    """Valida presença de scaffold mínimo executável em specialists."""
    output = dict(ctx.output)
    paths = _artifact_paths(output)
    if not paths:
        return PluginResult(output=output)

    errors: list[str] = []
    if ctx.agent_name == "frontend":
        _, errs = _has_frontend_scaffold(paths)
        errors.extend(errs)
    elif ctx.agent_name in ("backend", "devops"):
        _, errs = _has_backend_scaffold(paths)
        errors.extend(errs)

    if errors:
        output.setdefault("plugin_warnings", []).extend(errors)

    return PluginResult(output=output, errors=errors, modified=bool(errors))
