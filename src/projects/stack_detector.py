"""Detecção de stack frontend/backend em projetos gerados."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StackProfile:
    project_path: Path
    frontend_dir: Path | None = None
    backend_dir: Path | None = None
    has_frontend: bool = False
    has_backend: bool = False
    package_manager: str = "npm"
    framework: str = ""
    needs_npm_install: bool = False
    needs_pip_install: bool = False
    needs_playwright_browsers: bool = False
    has_api_tests: bool = False
    has_ui_tests: bool = False
    scripts: dict[str, str] = field(default_factory=dict)
    package_json_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frontend_dir": str(self.frontend_dir) if self.frontend_dir else None,
            "backend_dir": str(self.backend_dir) if self.backend_dir else None,
            "has_frontend": self.has_frontend,
            "has_backend": self.has_backend,
            "package_manager": self.package_manager,
            "framework": self.framework,
            "needs_npm_install": self.needs_npm_install,
            "needs_pip_install": self.needs_pip_install,
            "needs_playwright_browsers": self.needs_playwright_browsers,
            "has_api_tests": self.has_api_tests,
            "has_ui_tests": self.has_ui_tests,
            "scripts": self.scripts,
        }


def _read_package_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _detect_package_manager(base: Path) -> str:
    if (base / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (base / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _needs_install(base: Path, marker: Path, skip_if_installed: bool) -> bool:
    if not marker.is_file():
        return False
    node_modules = base / "node_modules"
    if not node_modules.is_dir():
        return True
    if not skip_if_installed:
        return True
    try:
        marker_mtime = marker.stat().st_mtime
        nm_mtime = node_modules.stat().st_mtime
        return marker_mtime > nm_mtime
    except OSError:
        return True


def _needs_pip(base: Path, dep_files: list[Path], skip_if_installed: bool) -> bool:
    existing = [f for f in dep_files if f.is_file()]
    if not existing:
        return False
    if not skip_if_installed:
        return True
    newest_dep = max(f.stat().st_mtime for f in existing)
    markers = list(base.glob("**/*.dist-info"))
    if not markers:
        return True
    newest_install = max(p.stat().st_mtime for p in markers[:50])
    return newest_dep > newest_install


def _infer_framework(pkg: dict[str, Any]) -> str:
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        raw = pkg.get(key) or {}
        if isinstance(raw, dict):
            deps.update({str(k).lower(): str(v) for k, v in raw.items()})

    parts: list[str] = []
    if "vite" in deps:
        parts.append("vite")
    if "react" in deps or "react-dom" in deps:
        parts.append("react")
    if "vue" in deps:
        parts.append("vue")
    if "next" in deps:
        parts.append("next")
    if "@angular/core" in deps:
        parts.append("angular")
    return "+".join(parts) if parts else "node"


def _has_playwright(base: Path, pkg: dict[str, Any]) -> bool:
    dev = pkg.get("devDependencies") or {}
    deps = pkg.get("dependencies") or {}
    if "@playwright/test" in dev or "@playwright/test" in deps:
        return True
    if (base / "playwright.config.ts").is_file() or (base / "playwright.config.js").is_file():
        return True
    e2e = base / "e2e"
    if e2e.is_dir() and (any(e2e.glob("*.spec.ts")) or any(e2e.glob("*.spec.js"))):
        return True
    return False


class StackDetector:
    def __init__(self, project_path: str | Path, *, skip_if_installed: bool = True) -> None:
        self.project_path = Path(project_path).resolve()
        self.skip_if_installed = skip_if_installed

    def detect(self, architecture: dict[str, Any] | None = None) -> StackProfile:
        arch = architecture or {}
        stack = str(arch.get("stack", "")).lower()

        profile = StackProfile(project_path=self.project_path)

        frontend_dir = self.project_path / "frontend"
        if not frontend_dir.is_dir() and (self.project_path / "package.json").is_file():
            frontend_dir = self.project_path
        if frontend_dir.is_dir() and (frontend_dir / "package.json").is_file():
            profile.frontend_dir = frontend_dir
            profile.has_frontend = True
            profile.package_json_path = frontend_dir / "package.json"
            pkg = _read_package_json(profile.package_json_path)
            profile.package_manager = _detect_package_manager(frontend_dir)
            profile.framework = _infer_framework(pkg)
            profile.scripts = {
                k: str(v)
                for k, v in (pkg.get("scripts") or {}).items()
                if isinstance(v, str)
            }
            if profile.package_manager == "pnpm":
                lock = frontend_dir / "pnpm-lock.yaml"
            elif profile.package_manager == "yarn":
                lock = frontend_dir / "yarn.lock"
            else:
                lock = frontend_dir / "package-lock.json"
            marker = lock if lock.is_file() else profile.package_json_path
            profile.needs_npm_install = _needs_install(
                frontend_dir, marker, self.skip_if_installed
            )
            profile.needs_playwright_browsers = _has_playwright(frontend_dir, pkg)
        elif any(k in stack for k in ("react", "vue", "angular", "vite", "frontend")):
            profile.has_frontend = bool(profile.frontend_dir)

        backend_dir = self.project_path / "backend"
        if not backend_dir.is_dir() and (self.project_path / "src").is_dir():
            backend_dir = self.project_path
        if backend_dir.is_dir():
            profile.backend_dir = backend_dir
            profile.has_backend = True
        elif "fastapi" in stack or "python" in stack:
            profile.has_backend = True
            profile.backend_dir = backend_dir if backend_dir.is_dir() else self.project_path

        dep_files: list[Path] = []
        search_base = profile.backend_dir or self.project_path
        for name in ("requirements.txt", "pyproject.toml", "Pipfile"):
            candidate = search_base / name
            if candidate.is_file():
                dep_files.append(candidate)
            root_candidate = self.project_path / name
            if root_candidate.is_file() and root_candidate not in dep_files:
                dep_files.append(root_candidate)
        profile.needs_pip_install = _needs_pip(search_base, dep_files, self.skip_if_installed)

        bd = profile.backend_dir or self.project_path
        api_dirs = [
            self.project_path / "tests" / "e2e",
            self.project_path / "tests" / "integration",
            bd / "tests" / "e2e",
        ]
        profile.has_api_tests = any(
            d.is_dir() and any(d.glob("test_*.py")) for d in api_dirs
        )

        fd = profile.frontend_dir or self.project_path
        ui_dirs = [fd / "e2e", self.project_path / "e2e"]
        profile.has_ui_tests = any(
            d.is_dir() and (any(d.glob("*.spec.ts")) or any(d.glob("*.spec.js")))
            for d in ui_dirs
        )
        if profile.has_ui_tests and profile.has_frontend:
            profile.needs_playwright_browsers = True

        return profile
