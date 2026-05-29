from pathlib import Path

from src.projects.stack_detector import StackDetector

FIXTURE = Path(__file__).parent / "fixtures" / "mini_frontend"


def test_detects_vite_react_frontend():
    profile = StackDetector(FIXTURE, skip_if_installed=False).detect(
        {"stack": "react vite"}
    )
    assert profile.has_frontend
    assert profile.frontend_dir == FIXTURE
    assert "vite" in profile.framework
    assert "react" in profile.framework
    assert profile.needs_npm_install
    assert profile.needs_playwright_browsers
    assert "dev" in profile.scripts


def test_detects_playwright_from_e2e_specs():
    profile = StackDetector(FIXTURE).detect()
    assert profile.has_ui_tests


def test_detects_package_manager_npm_by_default():
    profile = StackDetector(FIXTURE).detect()
    assert profile.package_manager == "npm"


def test_mini_app_backend_detection():
    root = Path(__file__).parent / "fixtures" / "mini_app"
    profile = StackDetector(root).detect({"stack": "python-fastapi"})
    assert profile.has_backend
    assert profile.has_api_tests
