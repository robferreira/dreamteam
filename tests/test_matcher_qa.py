from src.dream_teams.matcher import TeamMatcher


def test_matcher_always_includes_qa_for_new_feature():
    matcher = TeamMatcher()
    result = matcher.match("Criar API simples")
    assert "qa" in result.agents
    assert result.workflow == "new-feature"


def test_matcher_qa_keywords():
    matcher = TeamMatcher()
    result = matcher.match("Adicionar testes e2e com playwright")
    assert "qa" in result.agents
