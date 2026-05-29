# DreamTeam

Plataforma multi-agentes em Python com seleção de modelo em runtime, LangGraph, agentes Markdown e PostgreSQL + pgvector.

## Stack

- Python 3.11+, FastAPI, LangGraph, Pydantic
- PostgreSQL + pgvector, Redis
- ModelRouter para resolução de LLM por execução
- Projetos materializados em `projects/{slug}/`

## Quick start

```bash
cp .env.example .env
docker compose up -d postgres redis
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.main:app --reload
```

## API — fluxo recomendado

### 1. Configurar o DreamTeam (uma vez)

`POST /dream-teams` — define projeto + composição do time. **Não executa** o grafo.

```json
{
  "project": {
    "system_name": "Sistema de Pagamentos ACME",
    "system_description": "Plataforma para cobrança e conciliação",
    "owner_name": "Maria Silva",
    "owner_email": "maria@acme.com",
    "area": "financeiro",
    "stack_hint": "python-fastapi"
  },
  "workflow": "new-feature"
}
```

### 2. Executar com apenas um prompt

`POST /dream-teams/{dream_team_id}/run` — o time já está configurado; você envia só a necessidade.

```json
{
  "prompt": "Adicionar módulo de relatórios PDF com filtros por data"
}
```

Código gerado em `projects/{slug}/`.

### 3. Work your magic (recomendado para o usuário final)

`POST /work-your-magic` — pede só o que o usuário sabe e o sistema não infere bem.

| Campo | Obrigatório | Observação |
|-------|-------------|------------|
| `pedido` | sim | O que precisa ser feito |
| `responsavel` | sim | Nome do responsável |
| `sigla` | sim | Sigla única do projeto (ex.: `ESTQ`) |
| `nome_projeto` | não | Inferido do `pedido` se omitido |
| `descricao` | não | Usa o `pedido` se omitida |

```json
{
  "pedido": "Preciso de uma API REST de estoque com PostgreSQL e testes",
  "responsavel": "Maria Silva",
  "sigla": "ESTQ",
  "nome_projeto": "Sistema de Estoque ACME"
}
```

Stack, workflow, time de agentes e pasta do projeto são montados automaticamente.

## Outros endpoints

- `POST /tasks/continue` — retomar task (checkpointer)
- `GET /tasks/{id}` — status, steps, `project_path`
- `GET /projects/{slug}` — metadata e arquivos gerados
- `POST /agents/create` — agente customizado
- ~~`POST /tasks/create-system`~~ — **descontinuado (410)** — use `/dream-teams` + `/run` ou `/work-your-magic`

Docs: http://localhost:8000/docs

## Estrutura de agentes e recursos compartilhados

Todo o ecossistema de agentes vive em um **bundle** configurável via `AGENTS_BUNDLE_DIR` (padrão: `./agents`):

```
agents/                          # AGENTS_BUNDLE_DIR
├── default/                     # Agentes de sistema (architect.md, backend.md, ...)
│   └── _template.md
├── custom/                      # Agentes customizados via arquivo
├── skills/                      # Conhecimento — referenciado via ## SKILLS
│   ├── code-standards.md
│   └── ...
├── instructions/                # Regras globais — automático em todos os agentes
│   ├── global-rules.md
│   └── ...
└── plugins/                     # Validadores Python — referenciado via ## PLUGINS
    ├── registry.py
    └── builtin/
```

**Desacoplamento futuro:** aponte para um bundle externo:

```bash
AGENTS_BUNDLE_DIR=/opt/external-agent-system/bundle
```

**Resolução de agentes:** `custom/{nome}.md` → `default/{nome}.md` → PostgreSQL (API).

| Recurso | Como o agente usa |
|---------|-------------------|
| `skills/` | Lista stems em `## SKILLS` |
| `plugins/` | Lista nomes em `## PLUGINS` |
| `instructions/` | Injetado automaticamente (sem seção no `.md`) |

## Estrutura do projeto gerado

```
projects/{slug}/
├── project.json
├── README.md
├── .dreamteam/team.json
├── .dreamteam/manifest.json
├── docs/
└── src/
```
