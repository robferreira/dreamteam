import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from src.logging_config import get_logger
from src.memory.postgres import get_task_repository

logger = get_logger(__name__)


@dataclass
class WrittenFile:
    path: str
    agent: str
    artifact_type: str = "code"


@dataclass
class ProjectManifest:
    written_files: list[WrittenFile] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    agents_processed: list[str] = field(default_factory=list)


class ArtifactWriter:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path.resolve()
        self.project_path.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path | None:
        rel = relative_path.strip().lstrip("/").replace("\\", "/")
        if not rel or ".." in rel.split("/"):
            return None
        target = (self.project_path / rel).resolve()
        try:
            target.relative_to(self.project_path)
        except ValueError:
            return None
        return target

    def _extract_artifacts(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        artifacts = output.get("artifacts")
        if isinstance(artifacts, list):
            return artifacts
        if isinstance(output, dict) and "path" in output and "content" in output:
            return [output]
        return []

    def write_from_agent_output(
        self,
        agent: str,
        output: dict[str, Any],
    ) -> list[WrittenFile]:
        written: list[WrittenFile] = []

        for item in self._extract_artifacts(output):
            path_str = item.get("path")
            content = item.get("content")
            if not path_str or content is None:
                continue

            target = self._safe_path(str(path_str))
            if not target:
                logger.warning("artifact_path_rejected", agent=agent, path=path_str)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2)
            target.write_text(text, encoding="utf-8")

            artifact_type = item.get("type", "code")
            written.append(WrittenFile(path=str(path_str), agent=agent, artifact_type=artifact_type))

        return written

    async def write_from_agent_output_async(
        self,
        agent: str,
        output: dict[str, Any],
        *,
        task_id: UUID | None = None,
    ) -> list[WrittenFile]:
        written = self.write_from_agent_output(agent, output)
        if task_id:
            repo = get_task_repository()
            for f in written:
                await repo.save_artifact(
                    task_id=task_id,
                    agent=agent,
                    artifact_type=f.artifact_type,
                    content={"path": f.path},
                )
        return written

    def write_json_file(self, relative_path: str, data: dict[str, Any]) -> bool:
        target = self._safe_path(relative_path)
        if not target:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def write_markdown_file(self, relative_path: str, content: str) -> bool:
        target = self._safe_path(relative_path)
        if not target:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return True

    async def write_all_artifacts(
        self,
        artifacts: dict[str, Any],
        *,
        task_id: UUID | None = None,
    ) -> ProjectManifest:
        manifest = ProjectManifest()
        for agent, output in artifacts.items():
            if not isinstance(output, dict):
                continue
            manifest.agents_processed.append(agent)
            try:
                files = await self.write_from_agent_output_async(agent, output, task_id=task_id)
                manifest.written_files.extend(files)
            except Exception as e:
                manifest.errors.append(f"{agent}: {e}")
        return manifest

    def write_manifest(self, task_id: str, workflow: str, manifest: ProjectManifest) -> None:
        dreamteam_dir = self.project_path / ".dreamteam"
        dreamteam_dir.mkdir(exist_ok=True)
        data = {
            "task_id": task_id,
            "workflow": workflow,
            "agents_processed": manifest.agents_processed,
            "written_files": [
                {"path": f.path, "agent": f.agent, "type": f.artifact_type}
                for f in manifest.written_files
            ],
            "errors": manifest.errors,
            "files_count": len(manifest.written_files),
        }
        (dreamteam_dir / "manifest.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
