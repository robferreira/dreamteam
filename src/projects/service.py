import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

from src.api.schemas.project import ProjectMetadataSchema
from src.memory.postgres import get_project_repository
from src.settings import get_settings


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] or "project"


def _build_readme(metadata: dict[str, Any]) -> str:
    return f"""# {metadata['system_name']}

## Descrição
{metadata['system_description']}

## Responsável
- **Nome:** {metadata['owner_name']}
- **Email:** {metadata['owner_email']}
- **Área:** {metadata['area']}
{f"- **Organização:** {metadata['organization']}" if metadata.get('organization') else ""}

## Stack
{f"Preferência informada: `{metadata['stack_hint']}`" if metadata.get('stack_hint') else "A definir pelo arquiteto"}

---
Gerado por DreamTeam
"""


class ProjectService:
    def __init__(self) -> None:
        self._repo = get_project_repository()
        self._settings = get_settings()

    def _projects_root(self) -> Path:
        root = Path(self._settings.projects_dir)
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def _unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        counter = 1
        while await self._repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    async def create_project(self, metadata: ProjectMetadataSchema) -> dict[str, Any]:
        meta_dict = metadata.to_metadata_dict()
        base_slug = slugify(metadata.system_name)
        slug = await self._unique_slug(base_slug)
        root_path = f"projects/{slug}"
        project_dir = self._projects_root() / slug

        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".dreamteam").mkdir(exist_ok=True)

        project_json = {
            **meta_dict,
            "slug": slug,
            "root_path": root_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (project_dir / "project.json").write_text(
            json.dumps(project_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (project_dir / "README.md").write_text(_build_readme(meta_dict), encoding="utf-8")

        row = await self._repo.create(
            {
                "slug": slug,
                "system_name": metadata.system_name,
                "system_description": metadata.system_description,
                "owner_name": metadata.owner_name,
                "owner_email": str(metadata.owner_email),
                "area": metadata.area,
                "organization": metadata.organization,
                "stack_hint": metadata.stack_hint,
                "metadata_": metadata.additional_context or {},
                "root_path": root_path,
            }
        )

        return {
            "id": str(row.id),
            "slug": slug,
            "root_path": root_path,
            "project_path": str(project_dir),
            "metadata": meta_dict,
        }

    async def get_project(self, slug: str) -> Any | None:
        return await self._repo.get_by_slug(slug)

    async def get_project_by_id(self, project_id: UUID) -> Any | None:
        return await self._repo.get_by_id(project_id)

    async def update_stack_resolved(self, slug: str, stack: str) -> None:
        await self._repo.update(slug, {"stack_resolved": stack})
        project_dir = self._projects_root() / slug
        project_json_path = project_dir / "project.json"
        if project_json_path.exists():
            data = json.loads(project_json_path.read_text(encoding="utf-8"))
            data["stack_resolved"] = stack
            project_json_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def list_project_files(self, slug: str) -> list[str]:
        project_dir = self._projects_root() / slug
        if not project_dir.exists():
            return []
        files = []
        for path in project_dir.rglob("*"):
            if path.is_file() and ".dreamteam" not in path.parts:
                files.append(str(path.relative_to(project_dir)).replace("\\", "/"))
        return sorted(files)

    def get_project_path(self, slug: str) -> Path:
        return self._projects_root() / slug


@lru_cache
def get_project_service() -> ProjectService:
    return ProjectService()
