import re
from typing import Any

from src.api.schemas.project import ProjectMetadataSchema
from src.projects.service import slugify

STACK_PATTERNS: list[tuple[str, list[str]]] = [
    ("python-fastapi", ["fastapi", "python", "uvicorn", "pydantic", "postgresql", "postgres"]),
    ("node-nestjs", ["nestjs", "node", "typescript", "express"]),
    ("react-typescript", ["react", "typescript", "vite", "next.js", "nextjs"]),
    ("java-spring", ["spring", "java", "kotlin"]),
    ("dotnet", [".net", "c#", "aspnet", "asp.net"]),
]

AREA_KEYWORDS: dict[str, list[str]] = {
    "operacoes": ["estoque", "logistica", "inventario", "warehouse"],
    "financeiro": ["financeiro", "pagamento", "cobranca", "fatura", "billing"],
    "rh": ["rh", "funcionario", "folha", "colaborador"],
    "ti": ["api", "sistema", "software", "backend", "frontend", "integracao"],
}


def infer_stack_hint(text: str) -> str | None:
    lowered = text.lower()
    for stack, keywords in STACK_PATTERNS:
        if any(k in lowered for k in keywords):
            return stack
    return None


def infer_area(text: str) -> str:
    lowered = text.lower()
    for area, keywords in AREA_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            return area
    return "geral"


def infer_project_name_from_pedido(pedido: str) -> str:
    line = pedido.strip().split("\n")[0].strip()
    line = re.sub(r"\s+", " ", line)
    if len(line) >= 2:
        return line[:256]
    return "Nova demanda"


def infer_description_from_pedido(pedido: str) -> str:
    text = pedido.strip()
    if len(text) >= 10:
        return text
    return f"Demanda: {text}"


def project_slug_from_sigla(sigla: str) -> str:
    return slugify(sigla.lower())


def build_project_from_demand(
    *,
    pedido: str,
    responsavel: str,
    sigla: str,
    nome_projeto: str | None = None,
    descricao: str | None = None,
) -> ProjectMetadataSchema:
    """Monta metadados do projeto a partir do pedido e campos informados pelo usuário."""
    system_name = nome_projeto.strip() if nome_projeto else infer_project_name_from_pedido(pedido)
    system_description = descricao.strip() if descricao else infer_description_from_pedido(pedido)
    stack = infer_stack_hint(f"{pedido} {system_name} {system_description}")
    slug_base = project_slug_from_sigla(sigla)

    extra: dict[str, Any] = {
        "source": "work_your_magic",
        "sigla": sigla,
        "slug_base": slug_base,
        "pedido": pedido.strip(),
    }
    if stack:
        extra["stack_inferred"] = stack
    if not nome_projeto:
        extra["nome_projeto_inferred"] = True
    if not descricao:
        extra["descricao_inferred"] = True

    return ProjectMetadataSchema(
        system_name=system_name,
        system_description=system_description,
        owner_name=responsavel.strip(),
        owner_email=f"{slug_base}@projeto.dreamteam.app",
        area=infer_area(pedido),
        organization=sigla,
        stack_hint=stack,
        additional_context=extra,
    )


# Compatibilidade com testes legados
def infer_project_from_prompt(prompt: str) -> ProjectMetadataSchema:
    return build_project_from_demand(
        pedido=prompt,
        responsavel="DreamTeam",
        sigla="AUTO",
    )


def project_slug_from_prompt(prompt: str) -> str:
    return slugify(infer_project_name_from_pedido(prompt))
