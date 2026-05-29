---
name: bmad-code-review
description: Code review BMAD — orientado a acceptance criteria
tags: [reviewer, security]
---

## Review orientado a spec

- Verificar cada FR/user story relevante contra artifacts entregues
- Issues com severidade proporcional ao risco (high = bloqueia)
- `refactor_requests` acionáveis: agent + reason específico
- Scaffold incompleto (frontend sem package.json) = issue **high**

## Gate

- `approved=false` se qualquer issue high pendente
- `approved=false` se specialists executaram mas artifacts vazios
- Nunca aprovar código com secrets expostos
