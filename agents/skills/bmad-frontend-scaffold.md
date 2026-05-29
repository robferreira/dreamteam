---
name: bmad-frontend-scaffold
description: Scaffold frontend runnable — Vite/CRA completo
tags: [frontend]
---

## Scaffold obrigatório (React/TS)

Ao gerar frontend, incluir **todos** estes artifacts mínimos:

- `package.json` com scripts `dev`/`start` e dependências (react, vite ou react-scripts)
- `index.html` na raiz do app ou `frontend/`
- Entry point: `main.tsx`, `main.jsx` ou `index.tsx`
- Componentes referenciados pelo entry (ex.: `App.tsx`)

## API DreamTeam (endpoints reais)

Base: `http://localhost:8000` (ou `VITE_API_URL` / `REACT_APP_API_URL`)

| Endpoint | Uso |
|----------|-----|
| `GET /health` | status da API |
| `GET /tasks/{task_id}` | status, steps, progress |
| `GET /projects/{slug}` | metadados do projeto |
| `POST /work-your-magic` | iniciar execução |

**Nunca** inventar rotas como `/teams/status` — não existem na API DreamTeam.

## UX (Sally)

- Fluxos alinhados às user_stories
- Feedback de loading/erro nas chamadas HTTP
