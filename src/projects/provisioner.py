"""Provisionamento automático de dependências frontend/backend."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.logging_config import get_logger
from src.projects.stack_detector import StackDetector, StackProfile
from src.settings import get_settings

logger = get_logger(__name__)


class ProvisionError(Exception):
    """Falha de provisionamento que deve interromper a task."""


@dataclass
class ProvisionStep:
    command: str
    exit_code: int
    duration_seconds: float
    stdout_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "stdout_tail": self.stdout_tail,
        }


@dataclass
class ProvisionResult:
    target: str
    success: bool
    steps: list[ProvisionStep] = field(default_factory=list)
    detected_stack: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    skipped: bool = False
    failure_kind: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "success": self.success,
            "steps": [s.to_dict() for s in self.steps],
            "detected_stack": self.detected_stack,
            "error": self.error,
            "skipped": self.skipped,
            "failure_kind": self.failure_kind,
        }


def _tail(text: str, max_chars: int = 2000) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _run_cmd(cmd: list[str], *, cwd: Path, timeout: float) -> ProvisionStep:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        stdout = (proc.stdout or "") + (proc.stderr or "")
        duration = time.perf_counter() - start
        return ProvisionStep(
            command=" ".join(cmd),
            exit_code=proc.returncode,
            duration_seconds=duration,
            stdout_tail=_tail(stdout),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - start
        out = (exc.stdout or "") + (exc.stderr or "")
        return ProvisionStep(
            command=" ".join(cmd),
            exit_code=124,
            duration_seconds=duration,
            stdout_tail=_tail(str(out) + "\n[timeout]"),
        )
    except OSError as exc:
        duration = time.perf_counter() - start
        return ProvisionStep(
            command=" ".join(cmd),
            exit_code=127,
            duration_seconds=duration,
            stdout_tail=str(exc),
        )


def _resolve_executable(name: str) -> str | None:
    """Resolve executável no PATH; no Windows prioriza .cmd/.exe/.bat."""
    if sys.platform == "win32":
        for candidate in (f"{name}.cmd", f"{name}.exe", f"{name}.bat", name):
            path = shutil.which(candidate)
            if path:
                return path
        return None
    return shutil.which(name)


def _is_tool_execution_error(stdout_tail: str) -> bool:
    return "WinError 2" in stdout_tail or "WinError 193" in stdout_tail


def _require_tool(name: str, install_hint: str) -> str:
    path = _resolve_executable(name)
    if not path:
        raise ProvisionError(f"{install_hint}")
    return path


def _resolved_cmd(prof: StackProfile, base: Path, subcommand: list[str]) -> list[str]:
    pm = prof.package_manager
    exe = _resolve_executable(pm) or pm
    return [exe, *subcommand]


class ProjectProvisioner:
    def __init__(
        self,
        project_path: str | Path,
        architecture: dict[str, Any] | None = None,
        *,
        auto_provision: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.project_path = Path(project_path)
        self.architecture = architecture or {}
        self.auto_provision = (
            settings.auto_provision if auto_provision is None else auto_provision
        )
        self.skip_if_installed = settings.provision_skip_if_installed
        self.npm_timeout = float(settings.provision_npm_timeout_seconds)
        self.pip_timeout = float(settings.provision_pip_timeout_seconds)
        self._detector = StackDetector(
            self.project_path, skip_if_installed=self.skip_if_installed
        )
        self._profile: StackProfile | None = None

    @property
    def profile(self) -> StackProfile:
        if self._profile is None:
            self._profile = self._detector.detect(self.architecture)
        return self._profile

    def ensure_ready(self, profile: StackProfile | None = None) -> list[ProvisionResult]:
        """Garante deps instaladas (idempotente). Usado pelo QA."""
        if not self.auto_provision or not self.project_path.is_dir():
            return []
        prof = profile or self.profile
        results: list[ProvisionResult] = []
        if prof.has_frontend and prof.frontend_dir:
            results.append(self._provision_frontend(prof, force=False))
        if prof.has_backend and prof.backend_dir:
            results.append(self._provision_backend(prof, force=False))
        return results

    def provision_frontend(self) -> ProvisionResult:
        if not self.auto_provision:
            return ProvisionResult(
                target="frontend",
                success=True,
                skipped=True,
                detected_stack=self.profile.to_dict(),
            )
        prof = self.profile
        if not prof.has_frontend or not prof.frontend_dir:
            return ProvisionResult(
                target="frontend",
                success=True,
                skipped=True,
                detected_stack=prof.to_dict(),
            )
        return self._provision_frontend(prof, force=True)

    def provision_backend(self) -> ProvisionResult:
        if not self.auto_provision:
            return ProvisionResult(
                target="backend",
                success=True,
                skipped=True,
                detected_stack=self.profile.to_dict(),
            )
        prof = self.profile
        if not prof.has_backend:
            return ProvisionResult(
                target="backend",
                success=True,
                skipped=True,
                detected_stack=prof.to_dict(),
            )
        return self._provision_backend(prof, force=True)

    def _install_cmd(self, prof: StackProfile, base: Path) -> list[str]:
        pm = prof.package_manager
        if pm == "pnpm":
            lock = base / "pnpm-lock.yaml"
            if lock.is_file():
                return _resolved_cmd(prof, base, ["install", "--frozen-lockfile"])
            return _resolved_cmd(prof, base, ["install"])
        if pm == "yarn":
            lock = base / "yarn.lock"
            if lock.is_file():
                return _resolved_cmd(prof, base, ["install", "--frozen-lockfile"])
            return _resolved_cmd(prof, base, ["install"])
        lock = base / "package-lock.json"
        if lock.is_file():
            return _resolved_cmd(prof, base, ["ci"])
        return _resolved_cmd(prof, base, ["install"])

    def _provision_frontend(self, prof: StackProfile, *, force: bool) -> ProvisionResult:
        base = prof.frontend_dir
        assert base is not None
        detected = {
            "framework": prof.framework,
            "package_manager": prof.package_manager,
            **prof.to_dict(),
        }
        steps: list[ProvisionStep] = []

        try:
            _require_tool("node", "Node.js não encontrado no host. Instale Node 18+ para projetos frontend.")
            pm = prof.package_manager
            _require_tool(
                pm,
                f"{pm} não encontrado no PATH. Instale Node.js/npm para provisionar o frontend.",
            )
        except ProvisionError as exc:
            return ProvisionResult(
                target="frontend",
                success=False,
                detected_stack=detected,
                error=str(exc),
                failure_kind="tool_not_found",
            )

        if force or prof.needs_npm_install:
            step = _run_cmd(self._install_cmd(prof, base), cwd=base, timeout=self.npm_timeout)
            steps.append(step)
            if step.exit_code != 0:
                kind = "tool_not_found" if step.exit_code == 127 else "install_failed"
                if _is_tool_execution_error(step.stdout_tail):
                    kind = "tool_not_found"
                return ProvisionResult(
                    target="frontend",
                    success=False,
                    steps=steps,
                    detected_stack=detected,
                    error=f"Falha ao instalar dependências frontend: {step.stdout_tail}",
                    failure_kind=kind,
                )
        elif not (base / "node_modules").is_dir() and prof.package_json_path:
            step = _run_cmd(self._install_cmd(prof, base), cwd=base, timeout=self.npm_timeout)
            steps.append(step)
            if step.exit_code != 0:
                kind = "tool_not_found" if step.exit_code == 127 else "install_failed"
                if _is_tool_execution_error(step.stdout_tail):
                    kind = "tool_not_found"
                return ProvisionResult(
                    target="frontend",
                    success=False,
                    steps=steps,
                    detected_stack=detected,
                    error=f"Falha ao instalar dependências frontend: {step.stdout_tail}",
                    failure_kind=kind,
                )

        if prof.needs_playwright_browsers or prof.has_ui_tests:
            npx = _resolve_executable("npx") or "npx"
            pw_step = _run_cmd(
                [npx, "playwright", "install", "chromium"],
                cwd=base,
                timeout=self.npm_timeout,
            )
            steps.append(pw_step)
            if pw_step.exit_code != 0:
                return ProvisionResult(
                    target="frontend",
                    success=False,
                    steps=steps,
                    detected_stack=detected,
                    error=f"Falha ao instalar Playwright: {pw_step.stdout_tail}",
                )

        if not (base / "node_modules").is_dir():
            return ProvisionResult(
                target="frontend",
                success=False,
                steps=steps,
                detected_stack=detected,
                error="node_modules ausente após provisionamento",
            )

        if prof.scripts and "dev" not in prof.scripts:
            logger.warning("frontend_missing_dev_script", path=str(base))

        logger.info("frontend_provisioned", path=str(base), framework=prof.framework)
        return ProvisionResult(
            target="frontend",
            success=True,
            steps=steps,
            detected_stack=detected,
        )

    def _provision_backend(self, prof: StackProfile, *, force: bool) -> ProvisionResult:
        base = prof.backend_dir or self.project_path
        detected = prof.to_dict()
        steps: list[ProvisionStep] = []

        dep_files: list[tuple[Path, list[str]]] = []
        req = base / "requirements.txt"
        if req.is_file():
            dep_files.append((base, ["python", "-m", "pip", "install", "-r", "requirements.txt"]))
        root_req = self.project_path / "requirements.txt"
        if root_req.is_file() and root_req != req:
            dep_files.append(
                (self.project_path, ["python", "-m", "pip", "install", "-r", "requirements.txt"])
            )
        pyproject = base / "pyproject.toml"
        if pyproject.is_file():
            dep_files.append((base, ["python", "-m", "pip", "install", "-e", "."]))
        pipfile = base / "Pipfile"
        if pipfile.is_file():
            _require_tool("pipenv", "Pipenv não encontrado para instalar Pipfile.")
            dep_files.append((base, ["pipenv", "install"]))

        if not dep_files:
            if prof.has_api_tests:
                dep_files.append(
                    (
                        base,
                        [
                            "python",
                            "-m",
                            "pip",
                            "install",
                            "pytest",
                            "httpx",
                        ],
                    )
                )
            else:
                return ProvisionResult(
                    target="backend",
                    success=True,
                    skipped=True,
                    detected_stack=detected,
                )

        if not force and not prof.needs_pip_install and dep_files:
            return ProvisionResult(
                target="backend",
                success=True,
                skipped=True,
                detected_stack=detected,
            )

        for cwd, cmd in dep_files:
            step = _run_cmd(cmd, cwd=cwd, timeout=self.pip_timeout)
            steps.append(step)
            if step.exit_code != 0:
                return ProvisionResult(
                    target="backend",
                    success=False,
                    steps=steps,
                    detected_stack=detected,
                    error=f"Falha ao instalar dependências backend: {step.stdout_tail}",
                )

        if prof.has_api_tests:
            step = _run_cmd(
                ["python", "-m", "pip", "install", "pytest", "httpx"],
                cwd=base,
                timeout=self.pip_timeout,
            )
            if step.exit_code == 0:
                steps.append(step)

        logger.info("backend_provisioned", path=str(base))
        return ProvisionResult(
            target="backend",
            success=True,
            steps=steps,
            detected_stack=detected,
        )
