---
name: security-baseline
description: Baseline de segurança OWASP para código gerado
tags: [security, backend, frontend, devops]
---

## Input validation

- Validar e sanitizar toda entrada de usuário
- Usar Pydantic/parametrized queries — nunca concatenar SQL
- Limitar tamanho de payloads e rate limiting em endpoints públicos

## Secrets e auth

- Nunca commitar API keys, tokens ou senhas
- Senhas com hash (bcrypt/argon2), nunca plaintext
- JWT com expiração; refresh tokens quando necessário

## Headers e CORS

- CORS restrito a origens conhecidas em produção
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`

## Rejeitar entrega se

- Credenciais aparecem em código gerado
- Endpoints sensíveis sem autenticação documentada
- SQL injection ou XSS possíveis no código proposto
