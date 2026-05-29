from functools import lru_cache
from typing import Any

from plugins.base import PluginContext, PluginHandler, PluginResult
from plugins.builtin import artifact_validator, path_guard, qa_gate, qa_scaffold_validator, review_gate, scaffold_validator


class PluginRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, PluginHandler] = {}
        self.register("path_guard", path_guard)
        self.register("artifact_validator", artifact_validator)
        self.register("review_gate", review_gate)
        self.register("scaffold_validator", scaffold_validator)
        self.register("qa_scaffold_validator", qa_scaffold_validator)
        self.register("qa_gate", qa_gate)

    def register(self, name: str, handler: PluginHandler) -> None:
        self._handlers[name] = handler

    def get(self, name: str) -> PluginHandler | None:
        return self._handlers.get(name)

    def list_plugins(self) -> list[str]:
        return sorted(self._handlers.keys())

    async def run_pipeline(
        self,
        plugin_names: list[str],
        *,
        agent_name: str,
        output: dict[str, Any],
        project_path: str = "",
        extra: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        ctx = PluginContext(
            agent_name=agent_name,
            output=output,
            project_path=project_path,
            extra=extra or {},
        )
        all_errors: list[str] = []
        current = dict(output)
        for name in plugin_names:
            handler = self.get(name)
            if not handler:
                all_errors.append(f"Plugin não registrado: {name}")
                continue
            ctx.output = current
            result = handler(ctx)
            if hasattr(result, "__await__"):
                result = await result
            if isinstance(result, PluginResult):
                current = result.output
                all_errors.extend(result.errors)
            elif isinstance(result, dict):
                current = result
        return current, all_errors


@lru_cache
def get_plugin_registry() -> PluginRegistry:
    return PluginRegistry()
