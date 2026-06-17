# Exec Plan

## Goal

Prevent generated idea configs from running as research evidence until a human
approves them, while keeping local workflows deterministic and scriptable.

## Scope

In scope:

- Review queue artifact creation.
- CLI commands to inspect, approve, reject, archive, and run approved ideas.
- Gate enforcement for generated alpha-mining execution.
- Tests and documentation.

Out of scope:

- Auth or multi-user review policy.
- Managed registry-backed approvals.
- Live provider SDKs.

## Risk Classification

Risk flags:

- External provider behavior.
- Existing behavior.
- Public CLI contract.

Hard gates:

- External provider behavior.

## Work Phases

1. Add review queue domain helpers.
2. Write review queue artifacts during idea generation.
3. Enforce approval before generated config execution.
4. Add CLI review and run commands.
5. Validate with unit, integration, and CLI smoke tests.
6. Update product docs, decision record, and Harness story evidence.

## Stop Conditions

Pause for human confirmation if:

- Review needs role-scoped auth or immutable audit guarantees.
- Running generated configs requires external credentials or provider calls.
- Validation requirements need to be weakened.
