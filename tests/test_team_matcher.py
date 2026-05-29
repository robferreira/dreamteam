from src.dream_teams.matcher import TeamMatcher


def test_classify_bugfix():
    m = TeamMatcher()
    assert m.classify_workflow("Corrigir erro no login que retorna 500") == "bugfix"


def test_classify_refactor():
    m = TeamMatcher()
    assert m.classify_workflow("Refatorar modulo legado para melhor performance") == "refactor"


def test_classify_new_feature_default():
    m = TeamMatcher()
    assert m.classify_workflow("Criar API REST de estoque com PostgreSQL") == "new-feature"


def test_match_includes_backend_on_api_prompt():
    m = TeamMatcher()
    result = m.match("Criar API REST com autenticacao JWT")
    assert "backend" in result.agents
    assert result.workflow == "new-feature"
    assert result.rationale
