# Exec Plan

## Goal

Add a deterministic local adapter that stages and verifies a managed
Postgres/object-lock registry deployment bundle from an existing governance
pack, without credentials or real service mutation.

## Scope

In scope:

- Create a managed registry deployment module.
- Add CLI staging and verification commands.
- Add tests for valid staging, source governance failure, and tamper detection.
- Update README, product docs, architecture, test matrix, decision record, and
  Harness durable evidence.

Out of scope:

- Real Postgres connection.
- Cloud object storage writes.
- Credential management.
- Retention enforcement outside local artifacts.
- SQLite schema changes.

## Risk Classification

Risk flags:

- Data model: registry deployment artifacts and retention metadata.
- Audit/security: object-lock and credential-free guarantees.
- Public contracts: new CLI commands and deployment manifest.
- Existing behavior: registry export/governance boundary.

Hard gates:

- Audit/security.
- External system behavior is simulated only; real external calls are out of
  scope.

Lane: high-risk.

## Work Phases

1. Discovery: inspect registry export/governance code, CLI, product docs, and
   US-028 decision.
2. Design: define local dry-run deployment bundle and verifier.
3. Implementation: add module, CLI, tests, docs.
4. Verification: targeted tests, full pytest, compileall, pip check, git diff
   check, CLI stage/verify smoke.
5. Harness update: story status/evidence and detailed trace.
6. Commit and push to `origin/main`.

## Stop Conditions

Pause for human confirmation if:

- Real Postgres/cloud credentials become necessary.
- The implementation would contact external services.
- Validation gates would need to be weakened.
- A destructive data migration is required.
