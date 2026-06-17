# Exec Plan

## Goal

Make generated idea review decisions explainable by preserving append-only
audit events for queue creation, status changes, and run marking.

## Scope

In scope:

- JSONL review audit event schema.
- Audit events for queue creation, status updates, and marking configs ran.
- CLI command to print audit events.
- CLI actor attribution for review mutations.
- Tests and docs.

Out of scope:

- Authenticated actor identity.
- Immutable/tamper-proof storage.
- Registry-backed audit persistence.
- API review endpoints.

## Risk Classification

Risk flags:

- Audit/security.
- Existing behavior.
- Public CLI contract.

Hard gates:

- Audit/security.

## Work Phases

1. Add audit event model and JSONL helpers.
2. Append events from queue creation and review mutations.
3. Add CLI audit inspection and actor flag.
4. Extend tests for audit event order and content.
5. Update docs, decision record, and Harness evidence.

## Stop Conditions

Pause for human confirmation if:

- The story requires authenticated actors.
- Audit storage must be tamper-proof or retained centrally.
- Review events must be exposed via API.
