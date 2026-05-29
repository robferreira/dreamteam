from pathlib import Path
from unittest.mock import patch

from src.projects.provisioner import ProjectProvisioner, ProvisionStep

FIXTURE = Path(__file__).parent / "fixtures" / "mini_frontend"


def test_provision_frontend_fails_without_node():
    with patch("src.projects.provisioner.shutil.which", return_value=None):
        provisioner = ProjectProvisioner(FIXTURE, {"stack": "react vite"})
        result = provisioner.provision_frontend()
        assert not result.success
        assert "Node.js" in (result.error or "")


@patch("src.projects.provisioner._run_cmd")
@patch("src.projects.provisioner.shutil.which")
def test_provision_frontend_success(mock_which, mock_run, tmp_path):
    mock_which.side_effect = lambda name: f"/usr/bin/{name}"
    mock_run.return_value = ProvisionStep(
        command="npm install",
        exit_code=0,
        duration_seconds=1.0,
    )
    (tmp_path / "package.json").write_text(
        (FIXTURE / "package.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()

    provisioner = ProjectProvisioner(tmp_path, {"stack": "react vite"})
    result = provisioner.provision_frontend()
    assert result.success
    assert mock_run.called


@patch("src.projects.provisioner._run_cmd")
@patch("src.projects.provisioner.shutil.which")
def test_provision_frontend_fails_on_npm_error(mock_which, mock_run, tmp_path):
    mock_which.side_effect = lambda name: f"/usr/bin/{name}"
    mock_run.return_value = ProvisionStep(
        command="npm install",
        exit_code=1,
        duration_seconds=1.0,
        stdout_tail="npm ERR!",
    )
    (tmp_path / "package.json").write_text('{"name":"x","scripts":{"dev":"vite"}}', encoding="utf-8")

    provisioner = ProjectProvisioner(tmp_path, {"stack": "react vite"})
    result = provisioner.provision_frontend()
    assert not result.success
    assert result.error


def test_provision_skipped_when_auto_provision_disabled():
    provisioner = ProjectProvisioner(FIXTURE, auto_provision=False)
    result = provisioner.provision_frontend()
    assert result.skipped
    assert result.success
