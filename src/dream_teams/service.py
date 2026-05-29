import json
from functools import lru_cache
from typing import Any
from uuid import UUID

from src.api.schemas.project import ProjectMetadataSchema
from src.api.schemas.tasks import ModelOverrideSchema, WorkflowType
from src.memory.postgres import get_dream_team_repository, get_project_repository
from src.projects.service import get_project_service
from src.schemas.models import ModelSelection, ModelSource
from src.tasks.service import get_task_service
from src.workflows.loader import load_workflow


def _default_agents_for_workflow(workflow: str) -> list[str]:
    cfg = load_workflow(workflow)
    required = cfg.get("required_agents", [])
    specialists = cfg.get("specialists", [])
    return list(dict.fromkeys(required + specialists))


def _models_from_overrides(overrides: list[ModelOverrideSchema] | None) -> dict[str, Any]:
    if not overrides:
        return {}
    return {m.agent: m.model_dump(mode="json") for m in overrides}


def _project_metadata_from_row(project) -> dict[str, Any]:
    return {
        "system_name": project.system_name,
        "system_description": project.system_description,
        "owner_name": project.owner_name,
        "owner_email": project.owner_email,
        "area": project.area,
        "organization": project.organization,
        "stack_hint": project.stack_hint,
        "additional_context": project.metadata_ or {},
    }


class DreamTeamService:
    def __init__(self) -> None:
        self._repo = get_dream_team_repository()
        self._project_repo = get_project_repository()
        self._project_svc = get_project_service()

    def _write_team_json(self, slug: str, team_data: dict[str, Any]) -> None:
        path = self._project_svc.get_project_path(slug) / ".dreamteam" / "team.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(team_data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def create_team(
        self,
        project: ProjectMetadataSchema,
        workflow: str | None = None,
        agents: list[str] | None = None,
        models: list[ModelOverrideSchema] | None = None,
        user_id: str | None = None,
        matcher_source: str = "manual",
    ) -> dict[str, Any]:
        wf = workflow or WorkflowType.NEW_FEATURE.value
        created = await self._project_svc.create_project(project)
        slug = created["slug"]
        project_uuid = UUID(created["id"])
        team_agents = agents or _default_agents_for_workflow(wf)
        team_models = _models_from_overrides(models)

        row = await self._repo.create(
            {
                "project_uuid": project_uuid,
                "slug": slug,
                "workflow": wf,
                "agents": team_agents,
                "models": team_models,
                "matcher_source": matcher_source,
                "status": "ready",
                "user_id": user_id,
            }
        )

        team_payload = {
            "dream_team_id": str(row.id),
            "workflow": wf,
            "agents": team_agents,
            "models": team_models,
            "matcher_source": matcher_source,
            "status": "ready",
        }
        self._write_team_json(slug, team_payload)

        return {
            "dream_team_id": str(row.id),
            "project_slug": slug,
            "project_path": created["root_path"],
            "workflow": wf,
            "agents": team_agents,
            "status": "ready",
        }

    async def get_team(self, team_id: UUID):
        return await self._repo.get_by_id(team_id)

    async def run_team(
        self,
        team_id: UUID,
        prompt: str,
        models: list[ModelOverrideSchema] | None = None,
    ) -> dict[str, Any]:
        team = await self._repo.get_by_id(team_id)
        if not team:
            raise ValueError(f"DreamTeam não encontrado: {team_id}")

        project = await self._project_repo.get_by_id(team.project_uuid)
        if not project:
            raise ValueError("Projeto do time não encontrado")

        metadata = _project_metadata_from_row(project)
        project_path = str(self._project_svc.get_project_path(team.slug))

        user_models: list[ModelSelection] = []
        if models:
            for m in models:
                sel = m.to_selection()
                sel.source = ModelSource.USER_API
                user_models.append(sel)

        return await get_task_service().run_for_team(
            dream_team_id=team.id,
            project_uuid=team.project_uuid,
            project_slug=team.slug,
            project_path=project_path,
            project_metadata=metadata,
            workflow=team.workflow,
            agents=team.agents or [],
            team_models=team.models or {},
            prompt=prompt,
            user_id=team.user_id,
            user_models=user_models,
        )

    async def work_your_magic(
        self,
        *,
        pedido: str,
        responsavel: str,
        sigla: str,
        nome_projeto: str | None = None,
        descricao: str | None = None,
    ) -> dict[str, Any]:
        """Recebe demanda + dados essenciais; infere o restante e executa."""
        from src.dream_teams.demand_parser import build_project_from_demand, project_slug_from_sigla
        from src.dream_teams.matcher import TeamMatcher

        project = build_project_from_demand(
            pedido=pedido,
            responsavel=responsavel,
            sigla=sigla,
            nome_projeto=nome_projeto,
            descricao=descricao,
        )
        slug = project_slug_from_sigla(sigla)
        matcher = TeamMatcher()
        match = matcher.match(pedido, stack_hint=project.stack_hint)

        existing = await self._repo.get_by_slug(slug)
        if not existing:
            project_row = await self._project_repo.get_by_slug(slug)
            if project_row:
                existing = await self._repo.get_by_project(project_row.id)
        if existing and existing.status == "ready":
            team_id = existing.id
            match_rationale = f"{match.rationale}. Projeto existente reutilizado."
        else:
            model_overrides = [
                ModelOverrideSchema(
                    agent=agent,
                    provider=cfg.get("provider", "openai"),
                    model=cfg.get("model", "gpt-4o-mini"),
                    temperature=cfg.get("temperature"),
                )
                for agent, cfg in match.models.items()
                if isinstance(cfg, dict)
            ]
            created = await self.create_team(
                project=project,
                workflow=match.workflow,
                agents=match.agents,
                models=model_overrides or None,
                matcher_source="work_your_magic",
            )
            team_id = UUID(created["dream_team_id"])
            match_rationale = match.rationale

        team = await self._repo.get_by_id(team_id)
        run_result = await self.run_team(team_id, pedido)

        return {
            **run_result,
            "dream_team_id": str(team_id),
            "workflow": team.workflow if team else None,
            "agents": team.agents if team else [],
            "rationale": match_rationale,
        }


@lru_cache
def get_dream_team_service() -> DreamTeamService:
    return DreamTeamService()
