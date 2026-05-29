---
name: code-standards
description: Padrões de código Python/FastAPI para artifacts gerados
tags: [backend, frontend, database, devops, security, documentation]
---

## Padrões obrigatórios

- Python 3.11+ com type hints em funções públicas
- Nomes em snake_case para módulos/funções; PascalCase para classes
- Imports organizados: stdlib, third-party, local
- Docstrings breves em endpoints e funções públicas
- Sem secrets hardcoded — usar variáveis de ambiente

## Estrutura de projeto

- Código em `src/` com módulos por domínio
- Testes em `tests/` espelhando a estrutura de `src/`
- Docs em `docs/` (JSON + Markdown quando aplicável)
- Paths sempre relativos à raiz do projeto

## Artifacts

- Todo artifact de código deve ter `type`, `path`, `content` e `description`
- Conteúdo completo e executável — sem placeholders como `TODO` ou `...`
- Um arquivo por artifact; não agrupar múltiplos arquivos em um único artifact
