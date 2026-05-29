---
name: reviewer-checklist
description: Checklist objetivo para aprovação ou rejeição de entregas
tags: [reviewer]
---

## Aprovar somente se

- Artifacts cobrem o escopo da demanda e do task_plan
- Paths são relativos e válidos dentro do projeto
- Código segue type hints e estrutura definida na arquitetura
- Não há issues de severidade `high` pendentes

## Severidades

- **high**: bug, segurança, escopo não atendido, artifact inválido — **bloqueia aprovação**
- **medium**: qualidade, testes faltando, documentação incompleta — pode aprovar com ressalvas
- **low**: estilo, naming — registrar mas não bloquear

## refactor_requests

- Apontar agente responsável (`backend`, `frontend`, etc.)
- Motivo específico e acionável
- Uma request por issue agrupável

## Regra de assertividade

- Se existir qualquer issue `high`, `approved` DEVE ser `false`
- Nunca aprovar com `artifacts` vazios quando specialists foram executados
