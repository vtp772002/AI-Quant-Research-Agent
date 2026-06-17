# API Request Auth Audit Context

Date: 2026-06-17

## Status

Accepted

## Context

US-022 added API-key authentication and role-scoped access for the internal
FastAPI service. The existing request middleware already emits structured JSON
logs, but those logs do not explain which sanitized actor context authorized a
protected request or why an auth failure occurred.

Raw API keys must never appear in logs.

## Decision

Add sanitized authentication context to every API request log:

- Public routes record `auth_required=false` and `auth_result=not_required`.
- Protected successful requests record `auth_required=true`,
  `auth_result=ok`, `required_role`, `api_key_id`, and `role`.
- Protected failures record `auth_required=true`, the failed `auth_result`, and
  `required_role` without raw API keys.
- `api_key_id` is a masked identifier derived from the presented key, not the
  raw secret.

## Alternatives Considered

1. Keep auth context out of request logs. Rejected because role-scoped access is
   hard to operate without decision evidence.
2. Log raw API keys for easier debugging. Rejected because logs must not become
   secret stores.
3. Add a database-backed audit table now. Deferred because this story is only
   operational request logging, not durable product audit storage.

## Consequences

Positive:

- API access decisions are visible in existing structured logs.
- Auth failures can be diagnosed without exposing secrets.
- Future request audit persistence has a stable event shape to promote.

Tradeoffs:

- `api_key_id` is still a shared-key identifier, not a user identity.
- Logs remain operational records, not tamper-proof audit records.

## Follow-Up

- Add durable API audit storage if compliance-grade request audit becomes a
  product requirement.
