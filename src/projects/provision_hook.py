"""Hook de provisionamento após specialists frontend/backend."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.projects.provisioner import ProjectProvisioner, ProvisionResult


def _merge_provision_results(
    existing: list[dict[str, Any]] | None, new_result: ProvisionResult
) -> list[dict[str, Any]]:
    merged = list(existing or [])
    merged.append(new_result.to_dict())
    return merged


def _build_failure_context(agent_name: str, result: ProvisionResult) -> dict[str, Any]:
    return {
        "kind": "provision",
        "target": agent_name,
        "error": result.error or f"Provisionamento {agent_name} falhou",
        "steps": [s.to_dict() if hasattr(s, "to_dict") else s for s in result.steps],
        "failure_kind": result.failure_kind or "install_failed",
        "detected_stack": result.detected_stack,
        "recoverable": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def provision_after_specialist(
    state: dict[str, Any],
    agent_name: str,
) -> dict[str, Any] | None:
    """Provisiona deps após frontend/backend. Retorna patch de state ou None."""
    if agent_name not in ("frontend", "backend"):
        return None

    project_path = state.get("project_path")
    if not project_path:
        return None

    provisioner = ProjectProvisioner(
        project_path,
        state.get("architecture"),
    )

    if agent_name == "frontend":
        result = await asyncio.to_thread(provisioner.provision_frontend)
    else:
        result = await asyncio.to_thread(provisioner.provision_backend)

    patch: dict[str, Any] = {
        "provision_result": _merge_provision_results(state.get("provision_result"), result),
    }

    writer_path = Path(project_path)
    provision_file = writer_path / ".dreamteam" / "provision.json"
    provision_file.parent.mkdir(parents=True, exist_ok=True)
    all_results = patch["provision_result"]
    provision_file.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not result.success and not result.skipped:
        patch["failure_context"] = _build_failure_context(agent_name, result)
        patch["pending_retry_provision"] = False

    return patch
