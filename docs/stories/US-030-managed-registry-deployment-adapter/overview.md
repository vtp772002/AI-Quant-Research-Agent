# Overview

## Current Behavior

US-028 exports a verifiable registry governance pack. That pack is ready for
Postgres/object-store review, but there is still no deployment adapter contract
that turns it into a managed-storage handoff bundle with Postgres apply plan,
object-lock inventory, retention metadata, and verification.

## Target Behavior

The CLI can stage a deterministic local managed-registry deployment bundle from
an existing governance pack:

- verify the source governance pack first;
- write a Postgres apply plan that wraps the reviewed handoff SQL;
- copy governance artifacts into a local object-store simulation directory;
- write object-lock inventory rows with object keys, SHA-256 hashes, retention
  days, and legal-hold metadata;
- write a deployment manifest proving no credentials, network calls, or real
  managed service mutation occurred;
- verify the staged deployment bundle and fail on tampering.

## Affected Users

- Research operator reviewing registry promotion evidence for managed storage.
- Future developer replacing the local dry-run adapter with real Postgres and
  object-lock providers.
- Quant researcher relying on durable family-promotion evidence.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Connecting to a real Postgres instance.
- Writing to cloud object storage.
- Reading cloud credentials or secrets.
- Enforcing object lock outside the local bundle.
- Changing the SQLite registry schema.
