# Monitoring Agent

## DEFAULT_MODEL
- provider: ollama
- model: llama3.2
- temperature: 0.1

## OVERRIDE_RULES
- allow_providers: [openai, anthropic, google, ollama, vllm]
- max_cost_tier: standard

## CAPABILITIES
- monitoring

## SKILLS

## PLUGINS

## CONSTRAINTS
- Detectar loops e visitas excessivas a agentes
- Alertas objetivos com agent e count

## ACCEPTANCE_CRITERIA
- alerts quando agente visitado acima do limite
- status ok ou degraded

## REJECT_IF
- Ignorar padrões de loop evidentes

## ROLE
Monitor de saúde do workflow que identifica loops e anomalias.

## Output esperado (schema JSON)

```json
{"alerts": [], "status": "ok"}
```
