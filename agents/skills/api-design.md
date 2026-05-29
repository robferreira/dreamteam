---
name: api-design
description: Convenções REST e design de APIs
tags: [backend, architect, requirements]
---

## REST

- Recursos no plural: `/users`, `/orders`
- Verbos HTTP corretos: GET (leitura), POST (criação), PUT/PATCH (atualização), DELETE (remoção)
- Status codes: 200/201 sucesso, 400 validação, 401 auth, 403 forbidden, 404 not found, 500 erro interno

## Schemas

- Request/response com Pydantic models
- Campos obrigatórios explícitos; defaults documentados
- Paginação: `limit`, `offset` ou cursor-based quando listas forem grandes

## Documentação de API

- Cada endpoint deve ter método, rota, parâmetros e response schema
- Incluir exemplos de request/response no campo `apis` do JSON de saída
