from src.agents.output_schemas import (
    has_high_severity_issues,
    validate_agent_output,
)


def test_validate_reviewer_output_valid():
    output = {
        "approved": False,
        "issues": [{"severity": "medium", "description": "missing tests", "agent": "backend"}],
        "refactor_requests": [],
        "notes": "",
    }
    validated, errors = validate_agent_output("reviewer", output)
    assert not errors
    assert validated["approved"] is False


def test_validate_reviewer_output_invalid():
    output = {"approved": False, "issues": "not-a-list"}
    _, errors = validate_agent_output("reviewer", output)
    assert errors


def test_validate_backend_artifacts():
    output = {
        "artifacts": [
            {"type": "code", "path": "src/main.py", "content": "x=1", "description": "main"},
        ],
        "notes": "",
    }
    validated, errors = validate_agent_output("backend", output)
    assert not errors
    assert len(validated["artifacts"]) == 1


def test_validate_parse_error():
    output = {"parse_error": True, "raw_response": "not json"}
    _, errors = validate_agent_output("backend", output)
    assert errors
    assert "JSON" in errors[0]


def test_has_high_severity_issues():
    assert has_high_severity_issues(
        {"issues": [{"severity": "high", "description": "bug"}]}
    )
    assert not has_high_severity_issues(
        {"issues": [{"severity": "low", "description": "style"}]}
    )


def test_validate_requirements_output():
    output = {
        "needs_architecture": True,
        "functional_requirements": [{"id": "FR1", "description": "Login"}],
        "non_functional_requirements": [],
        "user_stories": [],
        "constraints": [],
        "notes": "",
    }
    validated, errors = validate_agent_output("requirements", output)
    assert not errors
    assert validated["needs_architecture"] is True
