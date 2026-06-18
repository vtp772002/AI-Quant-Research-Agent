# Managed Immutable Registry Governance

Date: 2026-06-18

## Status

Accepted

## Context

US-027 added cross-run experiment-family controls, but the local SQLite
registry remains mutable working storage. A family-level promotion verdict is
methodologically stronger than a single-run verdict, but the operational
evidence still needs a durable handoff artifact with hashes, retention
metadata, and tamper detection before any external investment process could
depend on it.

## Decision

Extend registry export with an artifact-first governance pack:

- `registry_governance_manifest.json` records schema version, owner, retention,
  optional previous-pack hash link, artifact hashes, final chain hash, and
  family evidence.
- `registry_hash_chain.ndjson` records one hash-chain row per exported registry
  record.
- CLI verification recomputes artifact and chain hashes and exits non-zero when
  the pack is inconsistent.

SQLite remains the default local registry. The governance pack is the immutable
evidence handoff for managed Postgres/object storage review; it does not
provision infrastructure or enforce cloud retention by itself.

## Alternatives Considered

1. Move directly to managed Postgres/object storage. Deferred because ownership,
   credentials, migrations, and retention enforcement need a separate platform
   story.
2. Keep only the existing export manifest. Rejected because it does not bind
   individual rows, family evidence, and retention metadata into a verifiable
   pack.
3. Make local SQLite append-only. Deferred because SQLite remains useful as
   working storage and would still not solve managed retention.

## Consequences

Positive:

- Registry exports now carry verifiable governance evidence.
- Tampering with exported records or hash-chain files is detected by the CLI.
- Future managed storage work gets a clear artifact contract.

Tradeoffs:

- Immutability is only as strong as the storage medium that preserves the pack.
- Managed Postgres migrations and object-lock policies remain future work.
- Pack correctness still depends on exporting the complete relevant registry
  universe for a family.

## Follow-Up

- Add managed Postgres/object-lock deployment after ownership, credentials, and
  retention enforcement are specified.
- Add separately locked institutional holdout datasets as a later methodology
  story.
