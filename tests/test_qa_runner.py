from pathlib import Path
from unittest.mock import patch

from src.qa.runner import QaTestRunner, merge_execution_results
from src.projects.stack_detector import StackDetector


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mini_app"


def test_server_manager_detects_layout():
    profile = StackDetector(FIXTURE_ROOT).detect({"stack": "python-fastapi react"})
    assert profile.has_backend
    assert profile.has_api_tests


def test_merge_execution_results_sets_e2e_passed():
    output = {"test_cases": [{"id": "TC1", "description": "x", "type": "api"}], "e2e_passed": False}
    execution = [
        {"suite": "api", "passed": True, "total": 1, "failed": 0},
        {"suite": "ui", "passed": True, "total": 1, "failed": 0},
    ]
    merged = merge_execution_results(output, execution)
    assert merged["e2e_passed"] is True
    assert len(merged["execution"]) == 2


@patch("src.qa.runner._run_command")
@patch("src.qa.runner.ServerManager")
def test_qa_runner_api_suite(mock_mgr_cls, mock_run):
    mock_mgr_cls.return_value.__enter__.return_value.detect_layout.return_value = {
        "backend_dir": FIXTURE_ROOT,
        "frontend_dir": None,
        "has_backend": True,
        "has_frontend": False,
        "has_api_tests": True,
        "has_ui_tests": False,
    }
    mock_mgr_cls.return_value.__enter__.return_value.start_api_server.return_value = "http://127.0.0.1:9999"
    mock_run.return_value = (0, "1 passed in 0.01s", 0.01)
    runner = QaTestRunner(FIXTURE_ROOT, {"stack": "python-fastapi"}, run_tests=True, auto_start_servers=False)
    results = runner.run()
    assert results
    assert results[0]["suite"] == "api"
    assert results[0]["passed"] is True


@patch("src.qa.runner._run_command")
def test_qa_runner_skipped_when_disabled(mock_run):
    runner = QaTestRunner(FIXTURE_ROOT, run_tests=False)
    results = runner.run()
    assert results == []
    mock_run.assert_not_called()
