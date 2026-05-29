from src.orchestrator.prompt_builder import PromptBuilder


def test_build_system_prompt_includes_constraints():
    prompt = PromptBuilder.build_system_prompt(
        "Persona base",
        instructions_context="--- INSTRUCTIONS GLOBAIS ---\nRegra global",
        constraints=["Nunca usar paths absolutos"],
        acceptance_criteria=["JSON válido"],
        reject_if=["Artifacts vazios"],
        skills_context="--- SKILLS ---\n### Skill: test",
    )
    assert "CONSTRAINTS" in prompt
    assert "ACCEPTANCE_CRITERIA" in prompt
    assert "REJECT_IF" in prompt
    assert "--- INSTRUCTIONS GLOBAIS ---" in prompt
    assert "--- SKILLS ---" in prompt
    assert "campo `error`" in prompt


def test_build_validation_retry_message():
    msg = PromptBuilder.build_validation_retry_message(
        "Execute backend",
        ["Campo artifacts ausente"],
    )
    assert "CORREÇÃO NECESSÁRIA" in msg
    assert "artifacts ausente" in msg
