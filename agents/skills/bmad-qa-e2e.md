# BMAD QA E2E — Test Architect (TEA)

Práticas distilladas do BMAD v6 para testes end-to-end no DreamTeam.

## Rastreabilidade

- Cada `acceptance_criteria` de user_story → pelo menos 1 `test_case` (TCn).
- Formato Given / When / Then na description.
- `story_id` ou FR id obrigatório para rastreio.

## Testes API (pytest + httpx)

```python
# tests/e2e/conftest.py
import os
import pytest
import httpx

@pytest.fixture
def api_base_url():
    return os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

@pytest.fixture
def client(api_base_url):
    with httpx.Client(base_url=api_base_url, timeout=30) as c:
        yield c
```

```python
# tests/e2e/test_api.py
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
```

- Preferir endpoints de `architecture.apis` e artifacts de backend.
- FastAPI: TestClient como alternativa se app importável de `src.main:app`.
- Sempre incluir teste de health/readiness quando app HTTP.

## Testes UI (Playwright)

```typescript
// frontend/e2e/app.spec.ts
import { test, expect } from '@playwright/test';

test('home loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('app-root')).toBeVisible();
});
```

```typescript
// frontend/playwright.config.ts
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  use: { baseURL: process.env.BASE_URL || 'http://127.0.0.1:5173' },
});
```

- Usar `data-testid` nos seletores quando possível.
- `package.json` deve ter `@playwright/test` em devDependencies e script `"test:e2e": "playwright test"`.

## Integração DreamTeam (quando app consome a plataforma)

Endpoints reais — nunca inventar:

| Endpoint | Uso |
|----------|-----|
| `GET /health` | Smoke da API DreamTeam |
| `GET /tasks/{task_id}` | Status, steps, progress |
| `GET /projects/{slug}` | Metadados do projeto |
| `POST /work-your-magic` | Disparo de task (mockar em testes) |

Base URL via `VITE_API_URL` ou env `API_BASE_URL`.

## Matriz requisito → teste

Documentar em `docs/test-plan.md`:

| ID | Requisito | Test Case | Tipo | Status |
|----|-----------|-----------|------|--------|

## Critérios de aprovação

- Todo AC crítico (P0/P1) tem teste E2E.
- Testes são independentes e idempotentes.
- Sem sleeps fixos — usar `expect` com timeout do Playwright.
- Falhas devem ter mensagens claras (assert com contexto).
