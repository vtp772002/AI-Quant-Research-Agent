# Exec Plan

## Goal

Expose review queue inspection, audit, status mutation, and approved-idea
execution through the existing role-scoped internal API.

## Scope

In scope:

- FastAPI review queue summary endpoint.
- FastAPI review audit endpoint.
- FastAPI review status update endpoint.
- FastAPI run-approved endpoint.
- Tests for route protection, status/audit behavior, and run-approved behavior.
- Docs, decision record, and Harness evidence.

Out of scope:

- Public API exposure.
- Managed review database.
- Multi-user approval workflow.
- User identity beyond sanitized API key actor ids.
- Live broker or vendor integration.

## Risk Classification

Risk flags:

- Audit/security.
- Auth.
- Authorization.
- Generated-research execution.
- Existing behavior.

Hard gates:

- Audit/security.
- Auth.
- Authorization.
- Full pytest.

## Work Phases

1. Add review queue Pydantic request models and FastAPI endpoints.
2. Reuse existing role dependency and sanitized API principal for audit actors.
3. Add tests proving route protection and audit-preserving review operations.
4. Update docs and durable decision.
5. Run full validation and update Harness evidence.

## Stop Conditions

Pause for human confirmation if:

- Raw API keys would need to be persisted.
- Review queue writes require multi-user approval semantics.
- Filesystem queue paths are no longer acceptable for internal trusted callers.
