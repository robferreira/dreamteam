from src.instructions.loader import get_instruction_loader


def test_list_instructions():
    loader = get_instruction_loader()
    names = loader.list_instructions()
    assert "global-rules" in names
    assert "json-output" in names
    assert "_template" not in names


def test_load_all_instructions():
    loader = get_instruction_loader()
    instructions = loader.load_all()
    assert len(instructions) >= 2
    names = {i.name for i in instructions}
    assert "global-rules" in names or any("global" in i.name for i in instructions)


def test_compose_prompt_block():
    loader = get_instruction_loader()
    block = loader.compose_prompt_block()
    assert "--- INSTRUCTIONS GLOBAIS ---" in block
    assert "JSON" in block


def test_load_single_instruction():
    loader = get_instruction_loader()
    instruction = loader.load("global-rules")
    assert instruction.content
    assert instruction.name == "global-rules"
