from src.agents.output_schemas import QaOutput, validate_agent_output


def test_validate_qa_output_valid():
    output = {
        "test_plan": "Plano E2E",
        "test_cases": [
            {"id": "TC1", "story_id": "US1", "description": "Health check", "type": "api"}
        ],
        "artifacts": [
            {
                "type": "code",
                "path": "tests/e2e/test_api.py",
                "content": "def test_health(): pass",
                "description": "API tests",
            }
        ],
        "execution": [],
        "e2e_passed": False,
        "notes": "",
    }
    validated, errors = validate_agent_output("qa", output)
    assert not errors
    assert validated["test_plan"] == "Plano E2E"


def test_validate_qa_output_invalid_test_case():
    output = {
        "test_cases": [{"id": "TC1"}],
        "artifacts": [],
        "e2e_passed": False,
    }
    _, errors = validate_agent_output("qa", output)
    assert errors
