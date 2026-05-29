# Agent Template

## DEFAULT_MODEL
- provider: openai
- model: gpt-4o-mini
- temperature: 0.2

## OVERRIDE_RULES
- allow_providers: [openai, anthropic, google, ollama, vllm]
- max_cost_tier: standard

## CAPABILITIES
- example

## SKILLS
- code-standards
- bmad-spec-driven

## PLUGINS
- path_guard
- scaffold_validator

## CONSTRAINTS
- Use paths relativos dentro do projeto
- Responda apenas com JSON válido

## ACCEPTANCE_CRITERIA
- Output conforme schema abaixo
- Campos obrigatórios preenchidos

## REJECT_IF
- JSON fora do schema
- Paths absolutos ou inválidos

## ROLE
Descrição clara da persona e responsabilidade do agente.

## PROJECT CONTEXT
Use os metadados do projeto injetados no prompt (system_name, owner, area, stack_hint).
Gere arquivos com paths relativos dentro do projeto (ex: src/..., docs/...).

## Recursos compartilhados (dentro do bundle `agents/`)

| Pasta | Uso | Referência no agente |
|-------|-----|----------------------|
| `agents/skills/` | Conhecimento e padrões | `## SKILLS` (lista de stems) |
| `agents/skills/bmad-*.md` | Práticas BMAD v6 adaptadas | Ver [`agents/bmad-mapping.md`](../bmad-mapping.md) |
| `agents/plugins/` | Validadores executáveis (Python) | `## PLUGINS` (lista de nomes) |
| `agents/instructions/` | Regras globais | Automático — aplicado a todos os agentes |

Configure o bundle via `AGENTS_BUNDLE_DIR=./agents` no `.env`.

## Output esperado (schema JSON)

```json
{
  "notes": ""
}
```
