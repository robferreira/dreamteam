from src.dream_teams.timeline_estimator import estimate_timeline


def test_bugfix_shorter_than_new_feature():
    agents = ["requirements", "planner", "backend", "reviewer", "memory"]
    simple = "Corrigir erro no endpoint POST"
    bugfix = estimate_timeline(prompt=simple, workflow="bugfix", agents=agents)
    feature = estimate_timeline(prompt=simple, workflow="new-feature", agents=agents)
    assert bugfix.estimated_duration_minutes < feature.estimated_duration_minutes


def test_complex_prompt_increases_duration():
    agents = ["requirements", "architect", "planner", "backend", "frontend", "reviewer", "memory"]
    simple = estimate_timeline(
        prompt="API REST simples",
        workflow="new-feature",
        agents=agents,
    )
    complex_prompt = estimate_timeline(
        prompt="Frontend React com docker e acompanhamento em tempo real via websocket",
        workflow="new-feature",
        agents=agents,
    )
    assert complex_prompt.estimated_duration_minutes > simple.estimated_duration_minutes
    assert "frontend" in complex_prompt.timeline_rationale or "docker" in complex_prompt.timeline_rationale


def test_timeline_has_required_fields():
    result = estimate_timeline(
        prompt="Criar API",
        workflow="new-feature",
        agents=["requirements", "backend"],
    )
    assert result.estimated_duration_minutes >= 5
    assert "minutos" in result.estimated_duration_label
    assert "display_timezone" in result.to_dict()
    assert "-03:00" in result.estimated_completion_at or "-02:00" in result.estimated_completion_at
    assert result.timeline_rationale
