# Managed Registry Deployment Adapter

Date: 2026-06-18

## Status

Accepted

## Context

US-028 made registry exports verifiable, and US-029 locked the institutional
holdout boundary. The next operational gap is deployment handoff: the project
needs a concrete Postgres/object-lock adapter contract before a real managed
storage integration can be safely built.

The current phase must remain deterministic and credential-free. It should
prove the artifact contract without mutating external systems.

## Decision

Add a local dry-run managed registry deployment adapter. It consumes a verified
registry governance pack and writes:

- `deployment_manifest.json`;
- `postgres_apply_plan.sql`;
- `object_lock_inventory.ndjson`;
- copied governance artifacts under a local `object_store/` directory.

The adapter records that no credentials were required and no network calls were
made. Verification recomputes hashes and fails on missing or changed staged
objects.

## Alternatives Considered

1. Direct Postgres/cloud object-lock integration. Rejected for this phase
   because credentials, ownership, and retention enforcement are not available.
2. Documentation-only handoff. Rejected because later real adapters need an
   executable manifest and verifier contract.
3. Extend the governance pack in place. Rejected because staging metadata such
   as object keys and apply-plan paths are deployment concerns, not source
   governance evidence.

## Consequences

Positive:

- Future managed storage work has a deterministic artifact contract.
- CI can prove staging and tamper detection without external dependencies.
- The boundary stays explicit about credentials and network behavior.

Tradeoffs:

- Retention remains simulated locally.
- SQL is still a reviewed apply plan, not an applied migration.
- Real provider integration remains future work.

## Follow-Up

- Replace the local dry-run adapter with credentialed provider adapters only
  after ownership, secrets handling, and retention enforcement are specified.
- Add operational runbooks for real managed storage once provider selection is
  made.
