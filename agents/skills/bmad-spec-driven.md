---
name: bmad-spec-driven
description: Metodologia spec-driven BMAD adaptada ao DreamTeam
tags: [requirements, architect, planner, backend, frontend, reviewer]
---

## Spec = fonte da verdade

- Toda decisão deve ser rastreável: demanda → FR/NFR → arquitetura → task → artifact
- Não contradizer artefatos já aprovados no estado do workflow
- Preferir entrega completa ou campo `error` explícito no JSON — nunca placeholders silenciosos

## Rastreabilidade

- Cada task do planner referencia requisitos (FR ids) quando aplicável
- Specialists implementam apenas o que está em specification + architecture + task_plan
- Reviewer verifica cobertura de acceptance criteria antes de aprovar
