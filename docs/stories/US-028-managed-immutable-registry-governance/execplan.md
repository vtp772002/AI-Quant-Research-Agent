# Exec Plan

## Goal

Add a verifiable immutable governance pack to registry export so research
promotion evidence can be handed off for managed storage review without relying
only on mutable local SQLite rows.

## Scope

In scope:

- Extend registry export artifacts with governance manifest and hash chain.
- Add CLI verification for exported governance packs.
- Include owner, retention, optional previous manifest hash, artifact hashes,
  final chain hash, and family evidence.
- Add deterministic tests for valid export, tamper detection, and invalid
  governance metadata.
- Update product docs, decision record, story packet, and Harness matrix.

Out of scope:

- Running or provisioning Postgres.
- Applying object-lock retention.
- Mutating historical registry rows.
- Changing family verdict methodology.
- Adding multi-user authorization.

## Risk Classification

Risk flags:

- Data model: registry evidence and retention metadata.
- Audit/security: immutable evidence and tamper detection.
- Public contracts: CLI export/verify surface.
- Existing behavior: registry export changes.

Hard gates:

- Audit/security.
- Data model and retention.

Lane: high-risk.

## Work Phases

1. Discovery: read registry export, registry storage, product docs, US-027
   follow-up, and validation matrix.
2. Design: choose artifact-first governance without managed storage side
   effects.
3. Validation planning: unit/integration tests for export and verifier;
   compile/full pytest before completion.
4. Implementation: extend `registry_export` and CLI args.
5. Verification: run targeted tests, full tests, compile, pip check, and CLI
   export/verify smoke.
6. Harness update: update story, decision, matrix, durable story row, and trace.

## Stop Conditions

Pause for human confirmation if:

- Implementation requires real Postgres credentials or cloud object-lock setup.
- Existing registry rows would need destructive migration.
- Verification requirements need to be weakened.
- Family promotion logic must change rather than only governance evidence.
