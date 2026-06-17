# Exec Plan

## Goal

Add sanitized authenticated actor and authorization decision context to API
request logs without logging secrets or adding a managed audit store.

## Scope

In scope:

- Auth context dataclass.
- Recording success and failure auth results in FastAPI request state.
- Request log payload fields for auth context.
- Tests proving public, success, failure, and no-raw-secret behavior.
- Docs, decision record, and Harness evidence.

Out of scope:

- Raw API key logging.
- User identities or tenant scopes.
- Durable request audit table.
- External log sink configuration.

## Risk Classification

Risk flags:

- Audit/security.
- Auth.
- Authorization.
- Existing behavior.

Hard gates:

- Audit/security.
- Auth.
- Authorization.

## Work Phases

1. Extend auth dependency to record request auth context.
2. Extend request log payload with sanitized auth fields.
3. Add tests for success, failure, public, and no-raw-secret logging.
4. Update docs and durable decision.
5. Run full validation and update Harness evidence.

## Stop Conditions

Pause for human confirmation if:

- Raw secrets would need to be logged.
- Request audit must be tamper-proof or persisted centrally.
- User identity or tenant-scoped authorization becomes required.
