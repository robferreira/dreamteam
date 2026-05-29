from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

PluginHandler = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


@dataclass
class PluginContext:
    agent_name: str
    output: dict[str, Any]
    project_path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    output: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    modified: bool = False
