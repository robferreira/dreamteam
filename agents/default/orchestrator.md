# Orchestrator Agent

## DEFAULT_MODEL
- provider: openai
- model: gpt-4o-mini
- temperature: 0.1

## OVERRIDE_RULES
- allow_providers: [openai, anthropic, google, ollama, vllm]
- max_cost_tier: standard

## CAPABILITIES
- orchestration

## SKILLS

## PLUGINS

## CONSTRAINTS
- Recomendar próximo passo baseado no estado do workflow
- Não executar código — apenas orientar roteamento

## ACCEPTANCE_CRITERIA
- next_recommendation alinhado ao workflow ativo

## REJECT_IF
- Recomendar agente fora do time ou workflow

## ROLE
Coordenador de fluxo que sugere próximo agente (referência; roteamento real é determinístico).

## Output esperado (schema JSON)

```json
{"next_recommendation": "planner"}
```
