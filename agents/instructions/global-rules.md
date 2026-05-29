---
name: global-rules
description: Regras globais de comportamento para todos os agentes
---

## Regras gerais

- Responda em JSON válido conforme o schema definido no agente
- Não invente paths, APIs ou features fora do escopo da demanda
- Em código Python gerado, use type hints em funções públicas
- Paths sempre relativos à raiz do projeto
- Nunca inclua secrets, tokens ou credenciais no conteúdo gerado
- Seja assertivo: prefira entregar completo ou reportar bloqueio via campo `error`

## Escopo

- Respeite o contexto do projeto e o estado do workflow injetado
- Não contradiga decisões já tomadas em specification, architecture ou review
