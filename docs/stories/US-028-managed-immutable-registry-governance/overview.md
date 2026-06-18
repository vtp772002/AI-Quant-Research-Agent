# Overview

## Current Behavior

The platform writes reproducibility manifests and records run metadata in a
local SQLite experiment registry. US-027 added experiment-family metadata and
family-level false-discovery controls, but the registry remains mutable local
working storage and registry export was only an offline Postgres/object-store
handoff.

That leaves promotion evidence operationally weak: a family verdict can be
recomputed from manifests, but there is no verifiable registry evidence pack
that ties exported rows, handoff SQL, retention metadata, and family promotion
evidence together.

## Target Behavior

Registry export produces an immutable governance evidence pack:

- `experiment_runs.ndjson` with exported registry rows.
- `postgres_upsert_experiment_runs.sql` for reviewed migration handoff.
- `registry_hash_chain.ndjson` with per-row hashes and chained hashes.
- `registry_governance_manifest.json` with schema version, owner, retention,
  previous-pack hash link, artifact hashes, final chain hash, and family
  evidence.

The CLI can verify the pack and returns non-zero when records, hash chain, or
artifact hashes no longer match.

## Affected Users

- Quant researcher reviewing whether promotion evidence is durable enough for
  the next research stage.
- Research operator exporting registry state for managed storage review.
- Future developer adding Postgres/object-lock deployment or locked holdout
  data controls.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Running a managed Postgres service.
- Applying database migrations automatically.
- Enforcing cloud object-lock retention from the local CLI.
- Multi-user authorization for family promotion.
- Separately locked institutional holdout datasets.
