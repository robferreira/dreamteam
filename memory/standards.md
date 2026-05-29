# Padrões de Código DreamTeam

## Linguagem e runtime

- Python 3.11+
- Type hints obrigatórios em funções e métodos públicos
- ModelRouter para toda execução de LLM na plataforma
- FastAPI para APIs; Pydantic v2 para schemas

## Estrutura de projeto gerado

```
projects/{slug}/
  src/           # código da aplicação
  tests/         # testes espelhando src/
  docs/          # specification.json, architecture.json, *.md
  README.md
  project.json
```

## Naming

- Módulos e funções: `snake_case`
- Classes: `PascalCase`
- Constantes: `UPPER_SNAKE_CASE`
- Endpoints REST: substantivos no plural (`/items`, `/users`)

## Artifacts (JSON de saída dos specialists)

Todo artifact deve conter:

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| type | sim | `code`, `config`, `test`, `doc` |
| path | sim | Relativo à raiz do projeto |
| content | sim | Conteúdo completo, sem placeholders |
| description | recomendado | Breve explicação do arquivo |

Regras:
- Paths relativos apenas — nunca absolutos ou com `..`
- Um arquivo por artifact
- Código executável — sem `TODO`, `...` ou pseudo-código

## Testes

- pytest como framework padrão
- Arquivo `tests/test_*.py` para cada módulo crítico
- Fixtures para DB/API quando aplicável
- Cobertura mínima: happy path + um caso de erro

## API REST

- Verbos HTTP corretos por operação
- Status codes semânticos (200, 201, 400, 401, 404, 500)
- Request/response tipados com Pydantic
- Documentar endpoints no campo `apis` do JSON de saída

## Segurança

- Sem secrets hardcoded
- Validação de input em toda borda
- Queries parametrizadas — nunca concatenar SQL
- Autenticação documentada em endpoints sensíveis

## Review

- Issues `high` bloqueiam aprovação
- Escopo da demanda deve estar coberto pelos artifacts
- Revisar consistência com architecture.json e specification.json
