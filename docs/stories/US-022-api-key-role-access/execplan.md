# Exec Plan

## Goal

Add a fail-closed API key and role boundary to the internal FastAPI service
without introducing multi-user auth infrastructure.

## Scope

In scope:

- API key parser for `AIQRA_API_KEYS`.
- Role hierarchy and FastAPI dependencies.
- Route-level role requirements.
- Tests for parser, missing keys, invalid keys, insufficient roles, route
  metadata, and allowed researcher execution.
- Docs, decision record, and Harness evidence.

Out of scope:

- JWT, OAuth, sessions, users, tenants, or password flows.
- Database-backed key storage.
- Key rotation and revocation.
- API actor audit logs.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Public API contract.
- Existing behavior.

Hard gates:

- Auth.
- Authorization.

## Work Phases

1. Add API auth helper.
2. Apply route dependencies.
3. Add deterministic tests.
4. Update docs and decision record.
5. Run full validation and API smoke.
6. Update Harness evidence.

## Stop Conditions

Pause for human confirmation if:

- The story needs user identities or tenants.
- A protected route needs to remain public beyond `/health`.
- Auth behavior cannot fail closed.
