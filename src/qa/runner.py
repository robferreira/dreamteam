"""Execução de testes E2E (pytest API + Playwright UI) no projeto gerado."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any

from src.logging_config import get_logger
from src.projects.provisioner import ProjectProvisioner
from src.qa.server_manager import ServerManager
from src.settings import get_settings

logger = get_logger(__name__)

_PYTEST_SUMMARY = re.compile(
    r"(?P<failed>\d+) failed(?:.*?)(?P<passed>\d+) passed|"
    r"(?P<passed_only>\d+) passed|"
    r"(?P<failed_only>\d+) failed",
    re.IGNORECASE,
)


def _tail(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _parse_pytest_output(stdout: str, exit_code: int) -> dict[str, Any]:
    failed = 0
    passed = 0
    skipped = 0

    for line in stdout.splitlines():
        lower = line.lower().strip()
        if " passed" in lower or " failed" in lower or " error" in lower:
            m = _PYTEST_SUMMARY.search(line)
            if m:
                if m.group("passed"):
                    passed = int(m.group("passed"))
                elif m.group("passed_only"):
                    passed = int(m.group("passed_only"))
                if m.group("failed"):
                    failed = int(m.group("failed"))
                elif m.group("failed_only"):
                    failed = int(m.group("failed_only"))

    if passed == 0 and failed == 0:
        if exit_code == 0:
            passed = 1
        else:
            failed = 1

    total = passed + failed + skipped
    failures: list[dict[str, Any]] = []
    if failed > 0:
        failures.append(
            {
                "test": "pytest suite",
                "message": _tail(stdout, 500),
                "agent": "backend",
            }
        )

    return {
        "suite": "api",
        "passed": exit_code == 0 and failed == 0,
        "total": total,
        "failed": failed,
        "skipped": skipped,
        "failures": failures,
    }


def _parse_playwright_output(stdout: str, exit_code: int) -> dict[str, Any]:
    failed = stdout.lower().count(" failed")
    passed = stdout.lower().count(" passed")
    if failed == 0 and passed == 0:
        if exit_code == 0:
            passed = 1
        else:
            failed = 1

    total = passed + failed
    failures: list[dict[str, Any]] = []
    if exit_code != 0:
        failures.append(
            {
                "test": "playwright suite",
                "message": _tail(stdout, 500),
                "agent": "frontend",
            }
        )

    return {
        "suite": "ui",
        "passed": exit_code == 0,
        "total": total,
        "failed": failed if exit_code != 0 else 0,
        "skipped": 0,
        "failures": failures,
    }


def _run_command(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, str, float]:
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        stdout = (result.stdout or "") + (result.stderr or "")
        duration = time.perf_counter() - start
        return result.returncode, stdout, duration
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        out = (exc.stdout or "") + (exc.stderr or "")
        return 124, out + "\n[timeout]", duration
    except OSError as exc:
        duration = time.monotonic() - start
        return 127, str(exc), duration


def _find_api_test_dir(project_path: Path, backend_dir: Path | None) -> Path | None:
    candidates = [
        project_path / "tests" / "e2e",
        project_path / "tests" / "integration",
    ]
    if backend_dir:
        candidates.extend(
            [
                backend_dir / "tests" / "e2e",
                backend_dir / "tests",
            ]
        )
    for d in candidates:
        if d.is_dir() and any(d.glob("test_*.py")):
            return d
    if (project_path / "tests").is_dir() and any((project_path / "tests").glob("test_*.py")):
        return project_path / "tests"
    return None


def _find_frontend_test_dir(frontend_dir: Path | None, project_path: Path) -> Path | None:
    candidates: list[Path] = []
    if frontend_dir:
        candidates.append(frontend_dir)
    candidates.append(project_path)
    for base in candidates:
        e2e = base / "e2e"
        if e2e.is_dir() and (any(e2e.glob("*.spec.ts")) or any(e2e.glob("*.spec.js"))):
            return base
    return None


class QaTestRunner:
    """Executa suites API e UI no project_path."""

    def __init__(
        self,
        project_path: str | Path,
        architecture: dict[str, Any] | None = None,
        *,
        run_tests: bool | None = None,
        auto_start_servers: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.project_path = Path(project_path)
        self.architecture = architecture or {}
        self.run_tests = settings.qa_run_tests if run_tests is None else run_tests
        self.auto_start_servers = (
            settings.qa_auto_start_servers if auto_start_servers is None else auto_start_servers
        )
        self.api_timeout = float(settings.qa_api_timeout_seconds)
        self.playwright_timeout = float(settings.qa_playwright_timeout_seconds)
        self._provisioned = False

    def ensure_provisioned(self) -> None:
        if self._provisioned or not self.project_path.is_dir():
            return
        provisioner = ProjectProvisioner(self.project_path, self.architecture)
        provisioner.ensure_ready()
        self._provisioned = True

    def run(self) -> list[dict[str, Any]]:
        if not self.run_tests or not self.project_path.is_dir():
            return []

        layout = ServerManager(self.project_path).detect_layout(self.architecture)
        results: list[dict[str, Any]] = []

        with ServerManager(
            self.project_path,
            auto_start=self.auto_start_servers,
            api_timeout=min(self.api_timeout, 60.0),
            frontend_timeout=min(self.playwright_timeout, 90.0),
        ) as servers:
            backend_dir = layout.get("backend_dir")
            frontend_dir = layout.get("frontend_dir")

            api_url: str | None = None
            ui_url: str | None = None

            if layout.get("has_api_tests") and backend_dir:
                api_url = servers.start_api_server(backend_dir)

            if layout.get("has_ui_tests") and frontend_dir:
                ui_url = servers.start_frontend_server(frontend_dir)

            api_result = self._run_api_tests(layout, api_url)
            if api_result:
                results.append(api_result)

            ui_result = self._run_ui_tests(layout, ui_url)
            if ui_result:
                results.append(ui_result)

        return results

    def _run_api_tests(
        self, layout: dict[str, Any], api_url: str | None
    ) -> dict[str, Any] | None:
        if not layout.get("has_api_tests"):
            return None

        backend_dir = layout.get("backend_dir") or self.project_path
        test_dir = _find_api_test_dir(self.project_path, backend_dir)
        if not test_dir:
            return {
                "suite": "api",
                "passed": False,
                "total": 0,
                "failed": 1,
                "skipped": 0,
                "duration_seconds": 0,
                "failures": [
                    {
                        "test": "discovery",
                        "message": "Nenhum diretório de testes API encontrado",
                        "agent": "qa",
                    }
                ],
                "command": "",
                "stdout_tail": "",
            }

        cwd = self.project_path
        env = None
        if api_url:
            import os

            env = dict(os.environ)
            env["API_BASE_URL"] = api_url

        try:
            rel = test_dir.relative_to(cwd)
            cmd = ["python", "-m", "pytest", str(rel), "-q", "--tb=short"]
        except ValueError:
            cmd = ["python", "-m", "pytest", str(test_dir), "-q", "--tb=short"]

        exit_code, stdout, duration = _run_command(
            cmd, cwd=cwd, env=env, timeout=self.api_timeout
        )
        parsed = _parse_pytest_output(stdout, exit_code)
        parsed["duration_seconds"] = duration
        parsed["command"] = " ".join(cmd)
        parsed["stdout_tail"] = _tail(stdout)
        return parsed

    def _run_ui_tests(
        self, layout: dict[str, Any], ui_url: str | None
    ) -> dict[str, Any] | None:
        if not layout.get("has_ui_tests"):
            return None

        frontend_dir = layout.get("frontend_dir")
        test_root = _find_frontend_test_dir(frontend_dir, self.project_path)
        if not test_root:
            return {
                "suite": "ui",
                "passed": False,
                "total": 0,
                "failed": 1,
                "skipped": 0,
                "duration_seconds": 0,
                "failures": [
                    {
                        "test": "discovery",
                        "message": "Nenhum spec Playwright encontrado em e2e/",
                        "agent": "qa",
                    }
                ],
                "command": "",
                "stdout_tail": "",
            }

        import os

        env = dict(os.environ)
        if ui_url:
            env["BASE_URL"] = ui_url

        cmd = ["npx", "playwright", "test"]
        exit_code, stdout, duration = _run_command(
            cmd, cwd=test_root, env=env, timeout=self.playwright_timeout
        )
        parsed = _parse_playwright_output(stdout, exit_code)
        parsed["duration_seconds"] = duration
        parsed["command"] = " ".join(cmd)
        parsed["stdout_tail"] = _tail(stdout)
        return parsed


def merge_execution_results(output: dict[str, Any], execution: list[dict[str, Any]]) -> dict[str, Any]:
    """Mescla resultados do runner no QaOutput."""
    merged = dict(output)
    merged["execution"] = execution
    if execution:
        merged["e2e_passed"] = all(r.get("passed") for r in execution)
    elif merged.get("test_cases"):
        merged["e2e_passed"] = bool(merged.get("e2e_passed"))
    return merged
