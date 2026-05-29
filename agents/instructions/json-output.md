---
name: json-output
description: Formato obrigatório de resposta JSON
---

## Formato de saída

- Responda **APENAS** com JSON válido — sem texto antes ou depois
- Não use blocos markdown (```json) na resposta final
- O JSON deve conformar ao schema documentado no agente

## Quando não puder cumprir

- Retorne JSON com campo `"error"` explicando o bloqueio de forma clara
- Não retorne JSON parcial ou inválido silenciosamente

## Validação

- Todos os campos obrigatórios do schema devem estar presentes
- Arrays vazios são aceitáveis quando o escopo não exige itens
