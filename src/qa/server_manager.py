"""Gerenciamento de servidores efêmeros para testes E2E."""

from __future__ import annotations

import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from src.logging_config import get_logger
from src.projects.stack_detector import StackDetector, StackProfile

logger = get_logger(__name__)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_url(url: str, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code < 500:
                return True
        except (httpx.HTTPError, OSError):
            pass
        time.sleep(0.5)
    return False


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[Any]
    base_url: str
    cwd: Path


@dataclass
class ServerManager:
    """Sobe e derruba servidores de API e frontend para E2E."""

    project_path: Path
    auto_start: bool = True
    api_timeout: float = 30.0
    frontend_timeout: float = 60.0
    _processes: list[ManagedProcess] = field(default_factory=list)
    _profile: StackProfile | None = None

    def __enter__(self) -> ServerManager:
        return self

    def __exit__(self, *args: object) -> None:
        self.stop_all()

    def stop_all(self) -> None:
        for mp in self._processes:
            try:
                mp.process.terminate()
                mp.process.wait(timeout=5)
            except Exception:
                try:
                    mp.process.kill()
                except Exception:
                    pass
        self._processes.clear()

    def detect_layout(self, architecture: dict[str, Any] | None = None) -> dict[str, Any]:
        profile = self.get_profile(architecture)
        return {
            "backend_dir": profile.backend_dir,
            "frontend_dir": profile.frontend_dir,
            "has_backend": profile.has_backend,
            "has_frontend": profile.has_frontend,
            "has_api_tests": profile.has_api_tests,
            "has_ui_tests": profile.has_ui_tests,
            "structure": (architecture or {}).get("structure") or {},
            "profile": profile,
        }

    def get_profile(self, architecture: dict[str, Any] | None = None) -> StackProfile:
        if self._profile is None:
            self._profile = StackDetector(self.project_path).detect(architecture)
        return self._profile

    def start_api_server(self, backend_dir: Path) -> str | None:
        if not self.auto_start:
            return None

        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"

        main_candidates = [
            backend_dir / "src" / "main.py",
            backend_dir / "main.py",
            backend_dir / "app.py",
        ]
        app_module = "src.main:app"
        for candidate in main_candidates:
            if candidate.is_file():
                if candidate.name == "main.py" and candidate.parent.name == "src":
                    app_module = "src.main:app"
                elif candidate.name == "main.py":
                    app_module = "main:app"
                elif candidate.name == "app.py":
                    app_module = "app:app"
                break

        cmd = [
            "python",
            "-m",
            "uvicorn",
            app_module,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            logger.warning("qa_api_server_start_failed", error=str(exc))
            return None

        health_urls = [f"{base_url}/health", f"{base_url}/", f"{base_url}/docs"]
        ready = False
        for url in health_urls:
            if _wait_for_url(url, timeout=self.api_timeout):
                ready = True
                break

        if not ready:
            proc.terminate()
            logger.warning("qa_api_server_health_timeout", base_url=base_url)
            return None

        self._processes.append(ManagedProcess("api", proc, base_url, backend_dir))
        return base_url

    def start_frontend_server(self, frontend_dir: Path) -> str | None:
        if not self.auto_start:
            return None

        if not (frontend_dir / "package.json").is_file():
            return None

        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"

        cmd = ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            logger.warning("qa_frontend_server_start_failed", error=str(exc))
            return None

        if not _wait_for_url(base_url, timeout=self.frontend_timeout):
            proc.terminate()
            logger.warning("qa_frontend_server_health_timeout", base_url=base_url)
            return None

        self._processes.append(ManagedProcess("frontend", proc, base_url, frontend_dir))
        return base_url

    @property
    def api_base_url(self) -> str | None:
        for mp in self._processes:
            if mp.name == "api":
                return mp.base_url
        return None

    @property
    def frontend_base_url(self) -> str | None:
        for mp in self._processes:
            if mp.name == "frontend":
                return mp.base_url
        return None
