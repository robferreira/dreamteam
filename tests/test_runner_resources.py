from src.instructions.loader import get_instruction_loader
from src.orchestrator.prompt_builder import PromptBuilder


def test_system_prompt_includes_global_instructions():
    loader = get_instruction_loader()
    instructions_context = loader.compose_prompt_block()
    prompt = PromptBuilder.build_system_prompt(
        "Persona base",
        instructions_context=instructions_context,
    )
    assert "--- INSTRUCTIONS GLOBAIS ---" in prompt
    assert "Persona base" in prompt
    assert prompt.index("Persona base") < prompt.index("--- INSTRUCTIONS GLOBAIS ---")


def test_instructions_before_skills_in_prompt():
    loader = get_instruction_loader()
    instructions_context = loader.compose_prompt_block()
    skills_context = "--- SKILLS ---\n### Skill: test"
    prompt = PromptBuilder.build_system_prompt(
        "Persona",
        instructions_context=instructions_context,
        skills_context=skills_context,
    )
    assert prompt.index("--- INSTRUCTIONS GLOBAIS ---") < prompt.index("--- SKILLS ---")
