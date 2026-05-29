import sys
from unittest.mock import patch

from src.projects.provisioner import _is_tool_execution_error, _resolve_executable


def test_resolve_executable_falls_back_to_cmd_on_windows():
    with patch.object(sys, "platform", "win32"):
        with patch("src.projects.provisioner.shutil.which") as mock_which:
            mock_which.side_effect = lambda name: {
                "npm": None,
                "npm.cmd": r"C:\Program Files\nodejs\npm.cmd",
            }.get(name)
            assert _resolve_executable("npm") == r"C:\Program Files\nodejs\npm.cmd"


def test_resolve_executable_prefers_cmd_over_npm_stub():
    with patch.object(sys, "platform", "win32"):
        with patch("src.projects.provisioner.shutil.which") as mock_which:
            mock_which.side_effect = lambda name: {
                "npm.cmd": r"C:\Program Files\nodejs\npm.cmd",
                "npm": r"C:\Program Files\nodejs\npm",
            }.get(name)
            assert _resolve_executable("npm") == r"C:\Program Files\nodejs\npm.cmd"


def test_resolve_executable_uses_path_when_available():
    with patch("src.projects.provisioner.shutil.which", return_value="/usr/bin/npm"):
        assert _resolve_executable("npm") == "/usr/bin/npm"


def test_resolve_executable_pnpm_cmd_on_windows():
    with patch.object(sys, "platform", "win32"):
        with patch("src.projects.provisioner.shutil.which") as mock_which:
            mock_which.side_effect = lambda name: {
                "pnpm": None,
                "pnpm.cmd": r"C:\Users\app\AppData\Roaming\npm\pnpm.cmd",
            }.get(name)
            assert _resolve_executable("pnpm") == r"C:\Users\app\AppData\Roaming\npm\pnpm.cmd"


def test_is_tool_execution_error_detects_winerror_193():
    assert _is_tool_execution_error("[WinError 193] %1 não é um aplicativo Win32 válido")


def test_is_tool_execution_error_detects_winerror_2():
    assert _is_tool_execution_error("[WinError 2] O sistema não pode encontrar o arquivo")
