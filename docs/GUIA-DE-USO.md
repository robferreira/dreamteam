# DreamTeam — Guia completo de uso

Documentação prática da API DreamTeam: o que cada endpoint faz, como funciona por baixo dos panos e exemplos prontos para uso.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Pré-requisitos e instalação](#2-pré-requisitos-e-instalação)
3. [Fluxos de uso recomendados](#3-fluxos-de-uso-recomendados)
4. [Referência de endpoints](#4-referência-de-endpoints)
5. [Workflows e agentes](#5-workflows-e-agentes)
   - [5.1 Pipeline do grafo](#51-pipeline-do-grafo-workflow-new-feature)
   - [5.2 Como o orquestrador escolhe o próximo agente](#52-como-o-orquestrador-escolhe-o-próximo-agente)
   - [5.3 Bundle de agentes](#53-bundle-de-agentes-agents_bundle_dir)
   - [5.4 Override de modelos](#54-override-de-modelos)
6. [Estados da task e acompanhamento](#6-estados-da-task-e-acompanhamento)
7. [Variáveis de ambiente](#7-variáveis-de-ambiente)
8. [Exemplos completos com curl](#8-exemplos-completos-com-curl)
9. [Erros comuns e soluções](#9-erros-comuns-e-soluções)

---

## 1. Visão geral

O DreamTeam é uma plataforma **multi-agentes** que:

1. Recebe uma **demanda** (o que você precisa construir ou corrigir).
2. Monta um **time de agentes** (requirements, architect, backend, etc.).
3. Executa um **grafo LangGraph** determinístico — cada agente chama um LLM, valida a saída e grava artefatos.
4. Materializa o código em `projects/{slug}/`.

```mermaid
flowchart TD
    Client[Cliente HTTP] --> API[FastAPI]
    API --> DreamTeam[DreamTeam Service]
    DreamTeam --> Task[Task Service]
    Task --> Graph[LangGraph]
    Graph --> Agents[Agentes LLM]
    Agents --> Projects[projects/slug/]
    Task --> DB[(PostgreSQL)]
    Agents --> RAG[(pgvector RAG)]
```

### Conceitos-chave

| Conceito | Descrição |
|----------|-----------|
| **DreamTeam** | Configuração persistida: projeto + workflow + lista de agentes + modelos |
| **Task** | Uma execução do grafo para uma demanda; retorna `task_id` para acompanhamento |
| **Workflow** | Template de fluxo (`new-feature`, `bugfix`, `refactor`) |
| **Agente** | Persona definida em Markdown no bundle `agents/` |
| **Bundle de agentes** | Pasta `agents/` (ou path externo via `AGENTS_BUNDLE_DIR`) com default, custom, skills, instructions e plugins |

---

## 2. Pré-requisitos e instalação

### Infraestrutura

- Python 3.11+
- Docker (PostgreSQL + Redis)
- Chave de API de pelo menos um provider LLM (OpenAI, Anthropic ou Google)

### Subir o ambiente

```bash
cp .env.example .env
# Edite .env e preencha OPENAI_API_KEY (ou outro provider)

docker compose up -d postgres redis
pip install -e ".[dev]"
alembic upgrade head
uvicorn src.main:app --reload
```

### Verificar saúde

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{"status": "ok", "version": "1.0.0"}
```

### Documentação interativa (Swagger)

Abra no navegador: **http://localhost:8000/docs**

---

## 3. Fluxos de uso recomendados

### Fluxo A — Work your magic (mais simples)

Ideal para **usuário final** que só sabe o pedido, responsável e sigla do projeto.

```
POST /work-your-magic
    → cria/reutiliza DreamTeam
    → escolhe workflow e agentes automaticamente
    → inicia execução
    → retorna task_id
GET /tasks/{task_id}
    → acompanha progresso
GET /projects/{slug}
    → vê arquivos gerados
```

### Fluxo B — DreamTeam manual (controle total)

Ideal quando você quer **definir projeto, workflow e agentes** explicitamente.

```
POST /dream-teams          → configura time (não executa)
POST /dream-teams/{id}/run → envia prompt e executa
GET /tasks/{task_id}       → acompanha
GET /projects/{slug}       → resultados
```

### Fluxo C — Retomar execução

Se a task foi pausada ou precisa de continuação com novo contexto:

```
POST /tasks/continue
GET /tasks/{task_id}
```

---

## 4. Referência de endpoints

Base URL padrão: `http://localhost:8000`

---

### 4.1 Sistema

#### `GET /health`

**O que faz:** Verifica se a API está no ar.

**Resposta:** `{ "status": "ok", "version": "..." }`

---

#### `GET /workflows`

**O que faz:** Lista os workflows disponíveis.

**Resposta:**

```json
{
  "workflows": ["new-feature", "bugfix", "refactor"]
}
```

**Como escolher:**

| Workflow | Quando usar |
|----------|-------------|
| `new-feature` | Funcionalidade nova completa (requirements → architect → specialists → reviewer) |
| `bugfix` | Correção de bug (sem architect; revisões limitadas) |
| `refactor` | Refatoração (começa em architect; sem requirements) |

---

### 4.2 Work your magic

#### `POST /work-your-magic`

**O que faz:** Fluxo **tudo-em-um**. Recebe demanda + dados essenciais, infere workflow/time, cria ou reutiliza projeto e **inicia a execução**.

**Como funciona internamente:**

1. `build_project_from_demand()` monta metadados do projeto a partir do pedido.
2. `TeamMatcher` classifica o workflow por palavras-chave no pedido.
3. Filtra specialists (backend, frontend, etc.) por keywords no texto.
4. Se já existir DreamTeam com a mesma sigla → reutiliza (busca por `metadata.sigla`, não pelo nome da pasta).
5. Caso contrário → `POST /dream-teams` implícito; pasta criada como `{sigla}_{nome_projeto}` (slugificado, ex.: `estq_sistema-de-estoque-acme`).
6. Executa o grafo e retorna `task_id`.

**Body (JSON):**

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `pedido` | sim | Demanda técnica (mín. 3 caracteres) |
| `responsavel` | sim | Nome do responsável |
| `sigla` | sim | Sigla única do projeto (ex.: `ESTQ`) — normalizada para maiúsculas |
| `nome_projeto` | não | Inferido do pedido se omitido |
| `descricao` | não | Usa o `pedido` se omitida |

**Exemplo:**

```json
{
  "pedido": "Preciso de uma API REST de estoque com PostgreSQL e testes",
  "responsavel": "Maria Silva",
  "sigla": "ESTQ",
  "nome_projeto": "Sistema de Estoque ACME"
}
```

**Resposta (200):**

```json
{
  "task_id": "uuid-da-task",
  "dream_team_id": "uuid-do-time",
  "project_slug": "estq_sistema-de-estoque-acme",
  "project_path": "projects/estq_sistema-de-estoque-acme",
  "workflow": "new-feature",
  "agents": ["requirements", "architect", "planner", "backend", "reviewer", "memory"],
  "rationale": "Workflow detectado: new-feature. ...",
  "status": "running",
  "timeline": {
    "estimated_duration_minutes": 45,
    "estimated_duration_label": "36–54 minutos",
    "estimated_completion_at": "2026-05-29T12:38:50-03:00",
    "display_timezone": "America/Sao_Paulo",
    "timeline_rationale": "Workflow new-feature, 8 agentes no time, escopo elevado (frontend, docker)"
  }
}
```

**Campo `timeline`:** estimativa heurística de conclusão calculada no momento do pedido (workflow, agentes e complexidade do texto). Não requer LLM extra.

**Erros:**

| Código | Motivo |
|--------|--------|
| 422 | Validação falhou (sigla inválida, campos obrigatórios ausentes) |

---

### 4.3 Dream Teams

#### `POST /dream-teams`

**O que faz:** Cria um **DreamTeam** (projeto + composição do time). **Não executa** o grafo.

**Como funciona internamente:**

1. Cria registro do projeto no PostgreSQL e pasta em `projects/{slug}/`.
2. Se `project.additional_context.sigla` estiver presente, o slug da pasta segue `{sigla}_{nome}` (ex.: `pagto_sistema-de-pagamentos-acme`); caso contrário, usa apenas o nome slugificado.
3. Persiste DreamTeam com workflow, agentes e overrides de modelo.
4. Grava `.dreamteam/team.json` no projeto.

**Body (JSON):**

```json
{
  "project": {
    "system_name": "Sistema de Pagamentos ACME",
    "system_description": "Plataforma para cobrança e conciliação bancária",
    "owner_name": "Maria Silva",
    "owner_email": "maria@acme.com",
    "area": "financeiro",
    "stack_hint": "python-fastapi",
    "organization": "ACME Corp",
    "additional_context": { "sigla": "PAGTO" }
  },
  "workflow": "new-feature",
  "agents": ["requirements", "architect", "planner", "backend", "reviewer", "memory"],
  "models": [
    {
      "agent": "backend",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.2
    }
  ],
  "user_id": "usuario-opcional"
}
```

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `project` | sim | Metadados do projeto |
| `workflow` | não | Default: `new-feature` |
| `agents` | não | Default: agentes do workflow |
| `models` | não | Override de modelo por agente |
| `user_id` | não | Identificador do usuário |

**Resposta (200):**

```json
{
  "dream_team_id": "uuid",
  "project_slug": "pagto_sistema-de-pagamentos-acme",
  "project_path": "projects/pagto_sistema-de-pagamentos-acme",
  "workflow": "new-feature",
  "agents": ["requirements", "architect", "..."],
  "status": "ready"
}
```

---

#### `POST /dream-teams/{team_id}/run`

**O que faz:** Executa o grafo para um DreamTeam **já configurado**. Você envia apenas o prompt.

**Parâmetro de path:** `team_id` — UUID retornado em `POST /dream-teams`.

**Body (JSON):**

```json
{
  "prompt": "Adicionar módulo de relatórios PDF com filtros por data",
  "models": [
    {
      "agent": "reviewer",
      "provider": "openai",
      "model": "gpt-4o",
      "temperature": 0.0
    }
  ]
}
```

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `prompt` | sim | Demanda técnica (mín. 3 caracteres) |
| `models` | não | Override de modelo só nesta execução |

**Resposta (200):**

```json
{
  "task_id": "uuid",
  "dream_team_id": "uuid",
  "project_slug": "pagto_sistema-de-pagamentos-acme",
  "project_path": "projects/pagto_sistema-de-pagamentos-acme",
  "status": "running",
  "message": "Execução iniciada",
  "timeline": {
    "estimated_duration_minutes": 30,
    "estimated_duration_label": "24–36 minutos",
    "estimated_completion_at": "2026-05-29T12:23:50-03:00",
    "display_timezone": "America/Sao_Paulo",
    "timeline_rationale": "Workflow new-feature, 6 agentes no time, escopo padrão"
  }
}
```

**Erros:**

| Código | Motivo |
|--------|--------|
| 400 | `team_id` não é UUID válido |
| 404 | DreamTeam não encontrado |

**Nota:** A execução é **assíncrona**. Use `GET /tasks/{task_id}` para acompanhar.

---

### 4.4 Tasks

#### `GET /tasks/{task_id}`

**O que faz:** Consulta status, steps executados e resultado de uma task.

**Parâmetro:** `task_id` — UUID retornado por `/run` ou `/work-your-magic`.

**Resposta (200):**

```json
{
  "id": "uuid",
  "project_id": "estq_sistema-de-estoque-acme",
  "project_slug": "estq_sistema-de-estoque-acme",
  "project_path": "projects/estq_sistema-de-estoque-acme",
  "files_written_count": 12,
  "workflow": "new-feature",
  "demand": "## CONTEXTO DO PROJETO\n...",
  "status": "completed",
  "result": {
    "approved": true,
    "artifacts": { "backend": { "artifacts": [...] } },
    "visited_agents": ["orchestrator", "requirements", "..."],
    "project_path": "projects/..."
  },
  "error": null,
  "thread_id": "task-uuid",
  "created_at": "2026-05-29T12:00:00",
  "updated_at": "2026-05-29T12:05:00",
  "timeline": {
    "estimated_duration_minutes": 45,
    "estimated_duration_label": "36–54 minutos",
    "estimated_completion_at": "2026-05-29T12:45:00-03:00",
    "timeline_rationale": "Workflow new-feature, 8 agentes no time",
    "display_timezone": "America/Sao_Paulo"
  },
  "current_agent": "backend",
  "progress": {
    "completed_count": 3,
    "current_agent": "backend",
    "label": "backend em execução"
  },
  "steps": [
    {
      "agent": "requirements",
      "status": "completed",
      "model_provider": "openai",
      "model_name": "gpt-4o-mini",
      "model_source": "agent_default",
      "tokens_estimated": 1500,
      "latency_ms": 3200,
      "created_at": "2026-05-29T09:01:00-03:00"
    },
    {
      "agent": "backend",
      "status": "running",
      "model_provider": "",
      "model_name": "",
      "model_source": "",
      "tokens_estimated": 0,
      "latency_ms": 0,
      "created_at": null
    }
  ]
}
```

**Campo `steps[].status`:** `completed` (agente já terminou), `running` (em execução agora), `failed` (erro no output do agente).

**Campos `current_agent` e `progress`:** indicam qual agente está rodando e quantos steps já concluíram.

**Status possíveis:**

| Status | Significado |
|--------|-------------|
| `running` | Grafo em execução |
| `interrupted` | Execução interrompida (restart do serviço ou worker inativo) — use `POST /tasks/continue` para retomar |
| `completed` | Finalizou com sucesso (review aprovado ou memory concluído) |
| `completed_with_issues` | Finalizou, mas review não aprovou totalmente |
| `failed` | Erro durante execução — ver campo `error` |

---

#### `POST /tasks/continue`

**O que faz:** Retoma uma task pausada via checkpointer LangGraph, opcionalmente com nova mensagem ou novos modelos.

**Body (JSON):**

```json
{
  "task_id": "uuid-da-task",
  "message": "Corrija o endpoint de login para usar JWT",
  "models": [
    {
      "agent": "backend",
      "provider": "openai",
      "model": "gpt-4o",
      "temperature": 0.2
    }
  ]
}
```

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `task_id` | sim | UUID da task |
| `message` | não | Contexto adicional anexado à demanda |
| `models` | não | Override de modelos na retomada |

**Resposta (200):**

```json
{
  "id": "uuid",
  "status": "running",
  "message": "Task retomada"
}
```

**Erros:**

| Código | Motivo |
|--------|--------|
| 404 | Task não encontrada ou já em processamento (lock Redis) |

---

#### `POST /tasks/create-system` (descontinuado)

**Retorna 410 Gone.** Use:

- `POST /dream-teams` + `POST /dream-teams/{id}/run`, ou
- `POST /work-your-magic`

---

### 4.5 Projects

#### `GET /projects/{slug}`

**O que faz:** Retorna metadados e lista de arquivos gerados de um projeto.

**Parâmetro:** `slug` — identificador do projeto (ex.: `estq_sistema-de-estoque-acme`).

**Resposta (200):**

```json
{
  "id": "uuid",
  "slug": "estq_sistema-de-estoque-acme",
  "system_name": "Sistema de Estoque ACME",
  "system_description": "...",
  "owner_name": "Maria Silva",
  "owner_email": "maria@acme.com",
  "area": "operacoes",
  "stack_hint": "python-fastapi",
  "stack_resolved": "python-fastapi",
  "root_path": "projects/estq_sistema-de-estoque-acme",
  "files": [
    "src/main.py",
    "docs/architecture.json",
    "docs/specification.json"
  ],
  "created_at": "2026-05-29T12:00:00"
}
```

**Erros:**

| Código | Motivo |
|--------|--------|
| 404 | Projeto não encontrado |

---

### 4.6 Agents

Gerenciamento de agentes customizados via **banco de dados**. Agentes de sistema ficam em `agents/default/*.md`.

#### `GET /agents/{agent_id}`

**O que faz:** Busca agente por slug (`backend`, `reviewer`) ou UUID (custom no DB).

**Resposta (200):**

```json
{
  "id": "backend",
  "slug": "backend",
  "name": "backend",
  "role": "Desenvolvedor backend senior...",
  "default_provider": "openai",
  "default_model": "gpt-4o-mini",
  "tools": [],
  "permissions": [],
  "restrictions": {},
  "visibility": "public",
  "is_custom": false,
  "source": "default"
}
```

**Campo `source`:**

| Valor | Origem |
|-------|--------|
| `default` | `agents/default/{slug}.md` |
| `file` | `agents/custom/{slug}.md` |
| `db` | Criado via `POST /agents/create` |

**Ordem de resolução ao executar:** `custom/` → `default/` → PostgreSQL.

---

#### `POST /agents/create`

**O que faz:** Cria agente customizado no PostgreSQL.

**Body (JSON):**

```json
{
  "name": "Meu Especialista PDF",
  "role": "Gera relatórios PDF",
  "prompt_md": "# PDF Agent\n\n## DEFAULT_MODEL\n- provider: openai\n- model: gpt-4o-mini\n- temperature: 0.2\n\n## ROLE\nEspecialista em PDF",
  "model": {
    "agent": "pdf-agent",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.2
  },
  "tools": ["path_guard", "artifact_validator"],
  "permissions": [],
  "restrictions": {},
  "visibility": "private"
}
```

**Erros:**

| Código | Motivo |
|--------|--------|
| 409 | Slug já existe (DB, custom file ou conflito com agente de sistema) |

---

#### `POST /agents/update`

**O que faz:** Atualiza agente customizado existente no DB.

**Body (JSON):**

```json
{
  "id": "uuid-do-agente-no-db",
  "role": "Nova descrição",
  "prompt_md": "...",
  "model": {
    "agent": "pdf-agent",
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.1
  }
}
```

---

## 5. Workflows e agentes

### 5.1 Pipeline do grafo (workflow `new-feature`)

O grafo LangGraph usa um **loop central**: todo agente termina e volta ao nó `orchestrator`, que decide o próximo passo via código Python (`route_next`). A ordem abaixo é a visão de alto nível — a sequência real é **condicional** (ver [§5.2](#52-como-o-orquestrador-escolhe-o-próximo-agente)).

```mermaid
flowchart LR
    Orch[orchestrator_node] -->|"route_next"| Next[proximo agente]
    Next --> Orch
    Orch -->|FINISH| Finalize[finalize]
```

Visão simplificada do pipeline `new-feature`:

```mermaid
flowchart LR
    REQ[requirements] --> ARCH[architect]
    ARCH --> PLAN[planner]
    PLAN --> SPEC[specialists]
    SPEC --> QA[qa]
    QA --> REV[reviewer]
    REV -->|approved| DOC[documentation]
    REV -->|rejected| SPEC
    DOC --> MEM[memory]
    MEM --> FINISH[finalize]
```

1. **requirements** — Especificação funcional (`docs/specification.json`)
2. **architect** — Stack e arquitetura (`docs/architecture.json`)
3. **planner** — Decomposição em tasks por specialist
4. **specialists** — backend, frontend, database, devops, security (em paralelo quando possível)
5. **qa** — Gera testes E2E (pytest + Playwright), executa no projeto e produz `qa_result`
6. **reviewer** — Gate de qualidade; falha E2E ou issues `high` bloqueiam aprovação
7. **documentation** — Docs finais (após review aprovado)
8. **memory** — Indexa decisões no RAG

### 5.2 Como o orquestrador escolhe o próximo agente

O orquestrador **não é um agente LLM**. É um roteador determinístico implementado em Python — o comentário em `src/graph/routing.py` deixa isso explícito: *"Roteamento determinístico — LangGraph NÃO decide modelos"*.

#### Ciclo de execução

```mermaid
flowchart LR
    Start[Task iniciada] --> Orch[orchestrator_node]
    Orch --> Route[route_next]
    Route --> Agent[Agente LLM executa]
    Agent --> Orch
    Route -->|FINISH| Final[finalize_node]
```

1. O grafo entra em `orchestrator_node` (`src/graph/nodes/agents.py`).
2. `route_next(state)` inspeciona o estado acumulado e retorna o nome do próximo nó (ou `"FINISH"`).
3. O agente escolhido executa (chama LLM, valida saída, grava artefatos).
4. O agente **sempre retorna** ao orquestrador — o ciclo se repete até `FINISH`.

#### Flags do state usadas na decisão

| Flag | Significado |
|------|-------------|
| `specification` | requirements já produziu a spec |
| `architecture` | architect já definiu a arquitetura |
| `task_plan` | planner já decompôs em tasks |
| `artifacts` | specialists já geraram código |
| `qa_result` | qa já gerou/executou testes E2E (`e2e_passed`, `execution`) |
| `review_result` | reviewer já avaliou |
| `memory_result` | memory já indexou no RAG |
| `active_agents` | Time permitido nesta execução |
| `workflow_config` | Regras do YAML (`new-feature`, `bugfix`, `refactor`) |
| `specialists_pending` / `specialists_done` | Fila de specialists a executar |

#### Ordem de prioridade do `route_next()`

A função em `src/graph/routing.py` aplica regras **em ordem fixa**:

1. **Parar** — se `force_stop` (monitoring detectou loop) ou `iteration_count >= MAX_ITERATIONS`
2. **requirements** — se está nos `required_agents` do workflow e ainda não há `specification`
3. **architect** — se `needs_architecture` e ainda não há `architecture`
4. **planner** — se ainda não há `task_plan` (e há spec ou arch, ou workflow é `refactor`)
5. **specialists** — via `get_specialists_for_plan()`:
   - Lê `task_plan.tasks[].agent` produzido pelo planner
   - Se o plano não especificar agents → usa todos os `specialists` do workflow YAML
   - Filtra por `active_agents` (time configurado)
   - **Mais de 1 pendente** → nó `specialists_parallel` (execução paralela)
   - **Só 1 pendente** → chama o specialist diretamente
6. **qa** — após todos os specialists de implementação, se `qa` está no time:
   - Gera testes API (pytest) e UI (Playwright) no projeto
   - Executa suites automaticamente (`QA_RUN_TESTS=true`)
   - Preenche `qa_result.e2e_passed` e `docs/qa-report.json`
7. **reviewer** — quando há `qa_result` (ou qa não está no time) e artefatos prontos:
   - Se reprovou com `refactor_requests` → manda de volta o specialist indicado (ex.: `backend`)
   - Issues com severidade `high` **bloqueiam** progresso até corrigir (até `max_revisions`)
   - `qa_result.e2e_passed=false` → reprovação via plugin `qa_gate`
8. **documentation** — após review aprovado (se estiver no time)
9. **memory** — indexa decisões no RAG
10. **cost_optimizer** — opcional, após memory
11. **FINISH** — encerra e grava manifest em `.dreamteam/manifest.json`

Em todo passo, o roteador verifica `_agent_in_team()`: se o agente não está em `active_agents`, **nunca é chamado**, mesmo que o pipeline normalmente o exigiria.

#### Quem monta o time (antes do grafo)

O orquestrador **não escolhe o time** — ele só roteia dentro do time já definido em `active_agents`:

| Origem | Como o time é montado |
|--------|----------------------|
| `POST /work-your-magic` | `TeamMatcher` (`src/dream_teams/matcher.py`) analisa keywords no prompt → workflow + specialists |
| `POST /dream-teams` | Lista explícita de `agents` no body |

**TeamMatcher — classificação de workflow:**

| Keywords no prompt | Workflow |
|--------------------|----------|
| bug, erro, corrigir, fix, hotfix… | `bugfix` |
| refatorar, refactor, legado, otimizar… | `refactor` |
| Demais casos | `new-feature` |

**TeamMatcher — filtro de specialists:** palavras como "API", "REST" → `backend`; "React", "UI" → `frontend`; "PostgreSQL" → `database`; etc. Se nenhuma keyword bater, inclui **todos** os specialists do workflow.

#### Papel do planner

O planner é um **agente LLM**, mas não decide o roteamento — apenas produz o `task_plan`. O roteador Python lê esse JSON depois:

```json
{
  "tasks": [
    {"id": "T1", "agent": "backend", "description": "Implementar CRUD de produtos", "priority": 1},
    {"id": "T2", "agent": "database", "description": "Schema e migrations", "priority": 2}
  ],
  "milestones": [],
  "notes": ""
}
```

Isso define **quais specialists** entram na fila — não **quando** (timing continua sendo regra fixa do `route_next`).

#### Diferenças por workflow

| Workflow | Comportamento |
|----------|---------------|
| `new-feature` | Pipeline completo: requirements → architect → planner → specialists → reviewer → memory |
| `bugfix` | Sem `architect` nos required; começa em requirements → planner |
| `refactor` | Sem `requirements`; começa em architect → planner |

Arquivos de configuração: `workflows/new-feature.yaml`, `workflows/bugfix.yaml`, `workflows/refactor.yaml`.

#### Exemplo passo a passo (`new-feature`)

```
Estado inicial: specification=null, architecture=null, task_plan=null
  → route_next → "requirements"

Após requirements: specification preenchido
  → route_next → "architect"

Após architect: architecture preenchido
  → route_next → "planner"

Após planner: task_plan com backend + database
  → route_next → "specialists_parallel"

Após specialists: artifacts preenchido
  → route_next → "reviewer"

Review aprovado
  → route_next → "documentation" (se no time)
  → route_next → "memory"
  → route_next → "FINISH"
```

#### Resumo

| Pergunta | Resposta |
|----------|----------|
| Quem decide o próximo agente? | `route_next()` em Python — não é LLM |
| Com base em quê? | Estado da task + workflow YAML + time ativo |
| Quem define quais specialists existem? | Planner (`task_plan`) ou workflow/TeamMatcher |
| Quem define o workflow? | TeamMatcher (automático) ou você (manual) |
| Existe agente LLM "orchestrator"? | Não — o nó `orchestrator` é só roteador |

#### Arquivos de referência

| Arquivo | Responsabilidade |
|---------|------------------|
| `src/graph/routing.py` | Lógica de roteamento (`route_next`, `get_specialists_for_plan`) |
| `src/graph/orchestrator.py` | Construção do grafo LangGraph |
| `src/graph/nodes/agents.py` | `orchestrator_node`, specialists paralelos, finalize |
| `src/dream_teams/matcher.py` | Montagem inicial do time (workflow + agents) |
| `workflows/*.yaml` | `required_agents`, `specialists`, `max_revisions` |

### 5.3 Bundle de agentes (`AGENTS_BUNDLE_DIR`)

```
agents/
├── default/        # Agentes de sistema (*.md)
├── custom/         # Agentes custom via arquivo
├── skills/         # Conhecimento — referenciado em ## SKILLS
├── instructions/   # Regras globais — injetadas em TODOS os agentes
└── plugins/        # Validadores Python — referenciados em ## PLUGINS
```

Para apontar bundle externo:

```bash
AGENTS_BUNDLE_DIR=/caminho/para/bundle-externo
```

#### Agentes inspirados no BMAD v6

Os agentes default incorporam personas e práticas do [BMAD-METHOD v6](https://github.com/bmad-code-org/BMAD-METHOD) (MIT), adaptadas ao formato JSON do DreamTeam:

| DreamTeam | Persona BMAD |
|-----------|--------------|
| requirements | Analyst + PM |
| architect | Architect |
| planner | Scrum Master / story planning |
| backend, frontend | Senior Dev + UX |
| reviewer | Code review + QA |
| documentation | Tech Writer |

Skills BMAD em `agents/skills/bmad-*.md`. Mapeamento completo: [`agents/bmad-mapping.md`](../agents/bmad-mapping.md).

Plugin `scaffold_validator` exige scaffold mínimo (ex.: frontend com `package.json` + entry point).

### 5.4 Override de modelos

Prioridade de resolução do modelo (maior → menor):

1. Override do orchestrator (economia forçada)
2. Override do usuário na requisição (`models` no body)
3. Modelo definido no workflow YAML
4. Modelo default do agente (`.md`)
5. Default do sistema

Providers configurados em `config/providers.yaml`: `openai`, `anthropic`, `google`, `ollama`, `vllm`.

**Fallback de provider:** se o workflow ou agente pedir um provider sem API key configurada (ex.: `anthropic` sem `ANTHROPIC_API_KEY`), o `ModelRouter` faz fallback automático para o próximo provider disponível (prioridade: OpenAI → Anthropic → Google). Isso evita falhas como `api_key Input should be a valid string` quando só `OPENAI_API_KEY` está preenchida.

---

## 6. Estados da task e acompanhamento

### Ciclo de vida

```
POST /run ou /work-your-magic
        ↓
   status: running
        ↓
   GET /tasks/{id}  (poll a cada 5–15s)
        ↓
   status: completed | completed_with_issues | failed
        ↓
   GET /projects/{slug}  (ver arquivos)
```

### Onde ficam os artefatos

```
projects/{slug}/
├── project.json
├── README.md
├── .dreamteam/
│   ├── team.json       # configuração do time
│   └── manifest.json   # arquivos escritos por agente
├── docs/
│   ├── specification.json
│   └── architecture.json
└── src/                # código gerado
```

### Campos úteis em `result`

| Campo | Descrição |
|-------|-----------|
| `qa_result` | qa já executou testes E2E (`e2e_passed`, `execution`, failures) |
| `approved` | Se o reviewer aprovou |
| `artifacts` | Output JSON de cada specialist |
| `review_result` | Issues e refactor_requests |
| `files_written_count` | Total de arquivos gravados |
| `visited_agents` | Sequência de agentes executados |

---

## 7. Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `DATABASE_URL` | postgres local | Conexão async PostgreSQL |
| `REDIS_URL` | redis local | Cache e locks |
| `OPENAI_API_KEY` | — | Provider OpenAI |
| `ANTHROPIC_API_KEY` | — | Provider Anthropic |
| `GOOGLE_API_KEY` | — | Provider Google |
| `OLLAMA_BASE_URL` | localhost:11434 | LLM local via Ollama |
| `PROJECTS_DIR` | `./projects` | Onde projetos são materializados |
| `AGENTS_BUNDLE_DIR` | `./agents` | Bundle completo de agentes |
| `MAX_ITERATIONS` | 20 | Limite de iterações do grafo |
| `MAX_AGENT_REVISITS` | 3 | Máximo de revisitas por agente |
| `REQUEST_TIMEOUT_SECONDS` | 120 | Timeout de requisições LLM |
| `DISPLAY_TIMEZONE` | `America/Sao_Paulo` | Fuso IANA para `estimated_completion_at` e timestamps na API |
| `QA_RUN_TESTS` | `true` | Executa pytest/Playwright após agente qa gerar testes |
| `QA_AUTO_START_SERVERS` | `true` | Sobe API e frontend efêmeros para E2E |
| `QA_API_TIMEOUT_SECONDS` | 120 | Timeout da suite pytest |
| `QA_PLAYWRIGHT_TIMEOUT_SECONDS` | 300 | Timeout da suite Playwright |
| `AUTO_PROVISION` | `true` | Instala deps após frontend/backend |
| `PROVISION_SKIP_IF_INSTALLED` | `true` | Pula install se node_modules/deps já atualizados |
| `PROVISION_NPM_TIMEOUT_SECONDS` | 300 | Timeout do npm/pnpm/yarn install |
| `PROVISION_PIP_TIMEOUT_SECONDS` | 180 | Timeout do pip install |
| `MAX_RECOVERY_ATTEMPTS` | 3 | Tentativas do orquestrador de recuperação antes de marcar task como `failed` |

**Provisionamento automático:** após o specialist `frontend` (e `backend`), o DreamTeam detecta stack e executa install (`npm ci`/`npm install`, `pip install`, Playwright browsers). Requer **Node.js 18+** no host. Em falha de install, a task **não encerra imediatamente** — o agente `recovery` analisa e pode reencaminhar correções (ex.: fix no `package.json`, retry de provision). Ver `provision_result` e `failure_context` em `GET /tasks/{id}`.

**Recuperação automática:** falhas de provisionamento, QA E2E ou review (após esgotar revisões) disparam o agente `recovery`. Enquanto houver tentativas (`MAX_RECOVERY_ATTEMPTS`), a task permanece `running` com `current_agent: recovery`. Campos expostos: `failure_context`, `recovery_result`, `recovery_attempts`, `recovery_history` (no `result` final).

**QA E2E:** requer Node.js/npm no host para Playwright quando o projeto tem frontend. O agente `qa` grava `docs/qa-report.json` e expõe `qa_result` em `GET /tasks/{id}`.

Horários como `estimated_completion_at` são retornados no fuso configurado (ex.: `2026-05-29T13:10:19-03:00`), não em UTC.

**Tasks órfãs:** ao reiniciar o uvicorn, tasks com status `running` passam automaticamente para `interrupted`. Se uma task ficar `running` sem heartbeat Redis por muito tempo, o `GET /tasks/{id}` também a marca como `interrupted`.

---

## 8. Exemplos completos com curl

### Exemplo 1 — Fluxo rápido (work your magic)

```bash
# 1. Executar
curl -s -X POST http://localhost:8000/work-your-magic \
  -H "Content-Type: application/json" \
  -d '{
    "pedido": "API REST de estoque com PostgreSQL, autenticação JWT e testes pytest",
    "responsavel": "Maria Silva",
    "sigla": "ESTQ",
    "nome_projeto": "Sistema de Estoque ACME"
  }' | jq .

# 2. Acompanhar (substitua TASK_ID)
curl -s http://localhost:8000/tasks/TASK_ID | jq '.status, .files_written_count, .steps[-1]'

# 3. Ver projeto gerado
curl -s http://localhost:8000/projects/SLUG_DO_PROJETO | jq '.files'
```

### Exemplo 2 — Fluxo manual com controle

```bash
# 1. Criar DreamTeam
curl -s -X POST http://localhost:8000/dream-teams \
  -H "Content-Type: application/json" \
  -d '{
    "project": {
      "system_name": "Portal de Vendas",
      "system_description": "Sistema de gestão de vendas B2B",
      "owner_name": "João Santos",
      "owner_email": "joao@empresa.com",
      "area": "comercial",
      "stack_hint": "python-fastapi"
    },
    "workflow": "new-feature",
    "agents": ["requirements", "architect", "planner", "backend", "reviewer", "memory"]
  }' | jq .

# 2. Executar (substitua TEAM_ID)
curl -s -X POST http://localhost:8000/dream-teams/TEAM_ID/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Implementar CRUD de clientes com validação Pydantic e testes"
  }' | jq .

# 3. Acompanhar
curl -s http://localhost:8000/tasks/TASK_ID | jq .
```

### Exemplo 3 — Bugfix

```bash
curl -s -X POST http://localhost:8000/work-your-magic \
  -H "Content-Type: application/json" \
  -d '{
    "pedido": "Corrigir erro 500 no endpoint POST /orders quando payload está vazio",
    "responsavel": "Dev Team",
    "sigla": "ORDFIX"
  }' | jq .
```

O matcher detectará `bugfix` pelas palavras "corrigir" e "erro".

---

## 9. Erros comuns e soluções

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| Task fica `running` muito tempo | Execução LLM lenta ou muitos agentes | Aguarde; verifique `steps` em `GET /tasks/{id}` |
| Task `failed` | API key inválida ou provider indisponível | Verifique `.env` e logs do uvicorn |
| `422` em work-your-magic | Sigla inválida ou campos curtos demais | Sigla com 2+ caracteres alfanuméricos |
| `404` em run | DreamTeam ID errado | Use UUID retornado em `POST /dream-teams` |
| Nenhum arquivo em `projects/` | Review bloqueou ou specialists falharam | Veja `result.review_result` na task |
| `Connection refused` PostgreSQL | Docker não subiu | `docker compose up -d postgres redis` |
| Agente custom não executa no grafo | Custom agents não estão em `AGENT_NODES` | Use agentes listados no workflow ou default |

---

## Referência rápida de endpoints

| Método | Endpoint | Ação |
|--------|----------|------|
| GET | `/health` | Health check |
| GET | `/workflows` | Listar workflows |
| POST | `/work-your-magic` | Fluxo completo automático |
| POST | `/dream-teams` | Criar time (sem executar) |
| POST | `/dream-teams/{id}/run` | Executar prompt no time |
| GET | `/tasks/{id}` | Status e steps da task |
| POST | `/tasks/continue` | Retomar task |
| GET | `/projects/{slug}` | Metadados e arquivos do projeto |
| GET | `/agents/{id}` | Consultar agente |
| POST | `/agents/create` | Criar agente custom (DB) |
| POST | `/agents/update` | Atualizar agente custom (DB) |

---

*Documentação gerada para DreamTeam v1.0.0 — Swagger interativo em `/docs`.*
