from functools import lru_cache
from typing import Any

import yaml

from src.config import WORKFLOWS_DIR
from src.schemas.models import ModelSelection, ModelSource


def list_workflow_names() -> list[str]:
    return sorted(p.stem for p in WORKFLOWS_DIR.glob("*.yaml"))


@lru_cache
def load_workflow(name: str) -> dict[str, Any]:
    path = WORKFLOWS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Workflow não encontrado: {name}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["name"] = data.get("name", name)
    return data


def parse_workflow_models(workflow: dict[str, Any]) -> dict[str, ModelSelection]:
    models_cfg = workflow.get("models") or {}
    result: dict[str, ModelSelection] = {}
    for agent, cfg in models_cfg.items():
        if isinstance(cfg, dict):
            result[agent] = ModelSelection(
                agent=agent,
                provider=cfg["provider"],
                model=cfg["model"],
                temperature=cfg.get("temperature"),
                max_tokens=cfg.get("max_tokens"),
                source=ModelSource.WORKFLOW,
            )
    return result
