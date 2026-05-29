from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.utils.datetime_display import format_display_datetime, get_display_timezone_name

WORKFLOW_BASE_MINUTES: dict[str, int] = {
    "new-feature": 18,
    "bugfix": 8,
    "refactor": 12,
}

AGENT_MINUTES: dict[str, int] = {
    "requirements": 2,
    "architect": 3,
    "planner": 2,
    "backend": 4,
    "frontend": 4,
    "database": 4,
    "devops": 4,
    "security": 4,
    "documentation": 2,
    "reviewer": 2,
    "memory": 1,
}

COMPLEXITY_KEYWORDS: list[tuple[str, int]] = [
    ("tempo real", 5),
    ("realtime", 5),
    ("websocket", 4),
    ("frontend", 4),
    ("docker", 3),
    ("agentes", 3),
    ("kubernetes", 3),
    ("autenticação", 2),
    ("jwt", 2),
]

REVISION_BUFFER_MINUTES = 5


@dataclass
class TimelineEstimate:
    estimated_duration_minutes: int
    estimated_duration_label: str
    estimated_completion_at: str
    timeline_rationale: str
    display_timezone: str

    def to_dict(self) -> dict:
        return {
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "estimated_duration_label": self.estimated_duration_label,
            "estimated_completion_at": self.estimated_completion_at,
            "timeline_rationale": self.timeline_rationale,
            "display_timezone": self.display_timezone,
        }


def _duration_label(minutes: int) -> str:
    low = max(1, int(minutes * 0.8))
    high = max(low + 1, int(minutes * 1.2))
    return f"{low}–{high} minutos"


def estimate_timeline(*, prompt: str, workflow: str, agents: list[str]) -> TimelineEstimate:
    base = WORKFLOW_BASE_MINUTES.get(workflow, WORKFLOW_BASE_MINUTES["new-feature"])
    agent_minutes = sum(AGENT_MINUTES.get(a, 2) for a in agents)

    text = prompt.lower()
    complexity_hits: list[str] = []
    complexity_minutes = 0
    for keyword, extra in COMPLEXITY_KEYWORDS:
        if keyword in text:
            complexity_minutes += extra
            complexity_hits.append(keyword)

    total = base + agent_minutes + complexity_minutes + REVISION_BUFFER_MINUTES
    total = max(5, total)

    completion = datetime.now(UTC) + timedelta(minutes=total)

    rationale_parts = [
        f"Workflow {workflow}",
        f"{len(agents)} agentes no time",
    ]
    if complexity_hits:
        rationale_parts.append(f"escopo elevado ({', '.join(complexity_hits[:4])})")
    else:
        rationale_parts.append("escopo padrão")

    return TimelineEstimate(
        estimated_duration_minutes=total,
        estimated_duration_label=_duration_label(total),
        estimated_completion_at=format_display_datetime(completion),
        timeline_rationale=", ".join(rationale_parts),
        display_timezone=get_display_timezone_name(),
    )
