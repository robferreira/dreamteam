from plugins.base import PluginContext, PluginResult

PLAYWRIGHT_CONFIG = "playwright.config.ts"
PLAYWRIGHT_SPEC_DIRS = ("frontend/e2e/", "e2e/")
API_TEST_DIRS = ("tests/e2e/", "tests/integration/")


def _artifact_paths(output: dict) -> list[str]:
    artifacts = output.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []
    paths: list[str] = []
    for item in artifacts:
        if isinstance(item, dict) and item.get("path"):
            paths.append(str(item["path"]).replace("\\", "/").lower())
    return paths


def _has_playwright_scaffold(paths: list[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    has_ui_test = any(
        p.endswith(".spec.ts") or p.endswith(".spec.js") or "/e2e/" in p
        for p in paths
    )
    if not has_ui_test:
        return True, errors

    has_config = any(p.endswith(PLAYWRIGHT_CONFIG) for p in paths)
    if not has_config:
        errors.append("Scaffold QA UI incompleto: falta playwright.config.ts")

    return not errors, errors


def _has_api_test_scaffold(paths: list[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    has_api_test = any(
        (p.startswith("tests/") or p.startswith("backend/tests/")) and p.endswith(".py")
        for p in paths
    )
    if not has_api_test:
        return True, errors

    has_e2e_dir = any(p.startswith(prefix) for p in paths for prefix in API_TEST_DIRS)
    if not has_e2e_dir:
        errors.append("Scaffold QA API incompleto: falta tests/e2e/ ou tests/integration/")

    return not errors, errors


async def qa_scaffold_validator(ctx: PluginContext) -> PluginResult:
    """Valida scaffold mínimo de testes E2E gerados pelo agente QA."""
    if ctx.agent_name != "qa":
        return PluginResult(output=dict(ctx.output))

    output = dict(ctx.output)
    paths = _artifact_paths(output)
    if not paths:
        return PluginResult(output=output)

    errors: list[str] = []
    _, ui_errs = _has_playwright_scaffold(paths)
    errors.extend(ui_errs)
    _, api_errs = _has_api_test_scaffold(paths)
    errors.extend(api_errs)

    if errors:
        output.setdefault("plugin_warnings", []).extend(errors)

    return PluginResult(output=output, errors=errors, modified=bool(errors))
