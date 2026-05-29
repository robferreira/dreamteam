import pytest
from pathlib import Path

from src.projects.artifact_writer import ArtifactWriter


@pytest.fixture
def writer(tmp_path):
    project = tmp_path / "test-project"
    project.mkdir()
    return ArtifactWriter(project)


def test_write_artifact_creates_file(writer, tmp_path):
    output = {
        "artifacts": [
            {"type": "code", "path": "src/main.py", "content": "print('hi')", "description": "main"}
        ]
    }
    files = writer.write_from_agent_output("backend", output)
    assert len(files) == 1
    assert (tmp_path / "test-project" / "src" / "main.py").read_text() == "print('hi')"


def test_reject_path_traversal(writer):
    output = {
        "artifacts": [
            {"type": "code", "path": "../../etc/passwd", "content": "bad"}
        ]
    }
    files = writer.write_from_agent_output("backend", output)
    assert len(files) == 0


def test_write_json_file(writer, tmp_path):
    ok = writer.write_json_file("docs/spec.json", {"ok": True})
    assert ok
    assert (tmp_path / "test-project" / "docs" / "spec.json").exists()
