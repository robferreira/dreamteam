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

## Spec-driven (BMAD adaptado)

- Decisões traceáveis: demanda → FR → arquitetura → task → artifact
- Não contradiga specification, architecture ou review já no estado do workflow
- Frontend: scaffold completo (package.json + entry) ou `error` explícito
- Documentação e código: apenas endpoints reais (API DreamTeam em `/health`, `/tasks/{id}`, etc.)
- Nunca inventar rotas como `/teams/status`
- QA E2E é gate obrigatório: código deve ser testável (health, data-testid, tests/e2e/)
- Agentes de implementação devem facilitar execução de pytest e Playwright pelo agente qa
- Após o specialist frontend, o DreamTeam executa npm/pnpm/yarn install automaticamente
- package.json deve ser completo — o sistema instala deps, não adiciona pacotes ausentes

## Escopo

- Respeite o contexto do projeto e o estado do workflow injetado
- Não contradiga decisões já tomadas em specification, architecture ou review
