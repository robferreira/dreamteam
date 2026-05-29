"""Team matching for dream teams."""

from dataclasses import dataclass, field
from typing import Any

from src.workflows.loader import load_workflow, parse_workflow_models

BUGFIX_KEYWORDS = ["bug", "erro", "error", "corrigir", "fix", "hotfix", "falha", "quebrado"]
REFACTOR_KEYWORDS = [
    "refatorar",
    "refactor",
    "legado",
    "performance",
    "reestruturar",
    "otimizar",
    "limpar codigo",
    "clean code",
]

AGENT_KEYWORDS: dict[str, list[str]] = {
    "frontend": ["frontend", "front-end", "react", "vue", "angular", "ui", "interface", "tela"],
    "backend": ["backend", "back-end", "api", "rest", "servidor", "endpoint"],
    "database": ["banco", "database", "postgres", "sql", "schema", "migracao", "migration"],
    "devops": ["devops", "docker", "kubernetes", "ci/cd", "deploy", "pipeline"],
    "security": ["seguranca", "security", "auth", "jwt", "oauth", "criptografia"],
    "documentation": ["documentacao", "documentation", "docs", "readme"],
    "qa": ["teste", "testes", "qa", "e2e", "playwright", "pytest", "qualidade"],
}

QA_ALWAYS_WORKFLOWS = {"new-feature", "bugfix"}


@dataclass
class TeamMatchResult:
    workflow: str
    agents: list[str]
    models: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""


class TeamMatcher:
    def classify_workflow(self, prompt: str) -> str:
        text = prompt.lower()
        if any(k in text for k in BUGFIX_KEYWORDS):
            return "bugfix"
        if any(k in text for k in REFACTOR_KEYWORDS):
            return "refactor"
        return "new-feature"

    def filter_agents_by_prompt(self, prompt: str, workflow_name: str) -> list[str]:
        workflow = load_workflow(workflow_name)
        required = list(workflow.get("required_agents", []))
        specialists = list(workflow.get("specialists", []))
        text = prompt.lower()

        matched_specialists = []
        for agent, keywords in AGENT_KEYWORDS.items():
            if agent in specialists and any(k in text for k in keywords):
                matched_specialists.append(agent)

        if not matched_specialists:
            matched_specialists = [s for s in specialists if s != "documentation"]

        agents = list(dict.fromkeys(required + matched_specialists))

        if workflow_name in QA_ALWAYS_WORKFLOWS and "qa" in required and "qa" not in agents:
            agents.insert(agents.index("reviewer") if "reviewer" in agents else len(agents), "qa")

        return agents

    def match(
        self,
        prompt: str,
        workflow: str | None = None,
        stack_hint: str | None = None,
    ) -> TeamMatchResult:
        wf = workflow or self.classify_workflow(prompt)
        agents = self.filter_agents_by_prompt(prompt, wf)
        models = {
            k: v.model_dump(mode="json")
            for k, v in parse_workflow_models(load_workflow(wf)).items()
        }

        rationale_parts = [f"Workflow detectado: {wf}"]
        if wf == "bugfix":
            rationale_parts.append("Pedido indica correção de bug ou erro")
        elif wf == "refactor":
            rationale_parts.append("Pedido indica refatoração ou melhoria estrutural")
        else:
            rationale_parts.append("Pedido indica nova funcionalidade ou sistema")

        specialist_names = [a for a in agents if a not in load_workflow(wf).get("required_agents", [])]
        if specialist_names:
            rationale_parts.append(f"Especialistas selecionados: {', '.join(specialist_names)}")
        if stack_hint:
            rationale_parts.append(f"Stack sugerida: {stack_hint}")

        return TeamMatchResult(
            workflow=wf,
            agents=agents,
            models=models,
            rationale=". ".join(rationale_parts),
        )
