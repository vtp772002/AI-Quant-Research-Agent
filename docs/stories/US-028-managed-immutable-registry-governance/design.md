# Design

## Domain Model

`RegistryExport` now includes governance artifacts in addition to the existing
records, manifest, and SQL handoff files.

`RegistryGovernanceVerification` reports whether an export directory is
internally consistent, which files were checked, and the concrete errors found.

Governance evidence is artifact-first. The local SQLite registry remains
mutable working storage; the export pack is the reviewable immutable handoff.

## Application Flow

Export:

1. Read registry rows through `experiment_registry.list_runs`.
2. Write canonical NDJSON records.
3. Write reviewed Postgres upsert SQL.
4. Write a per-row hash chain over the exported records.
5. Write a governance manifest containing artifact hashes, owner, retention,
   optional previous governance manifest hash, final chain hash, and family
   evidence.

Verify:

1. Load `registry_governance_manifest.json`.
2. Verify schema version.
3. Verify artifact existence and SHA-256 hashes.
4. Recompute record hashes and chained hashes.
5. Return valid/invalid status without mutating the pack.

## Interface Contract

Existing export command remains valid:

```bash
python -m quant_research_agent.main --export-registry results/registry_export
```

New optional export metadata:

```bash
python -m quant_research_agent.main \
  --export-registry results/registry_export \
  --registry-owner research-ops \
  --registry-retention-days 730 \
  --previous-governance-manifest results/previous/registry_governance_manifest.json
```

Verification:

```bash
python -m quant_research_agent.main --verify-registry-governance results/registry_export
```

The verification command exits `0` only when the governance pack is internally
consistent. It exits `1` and emits machine-readable errors when tampering or
corruption is detected.

## Data Model

No SQLite schema migration is required. Governance metadata is stored in export
artifacts:

- `registry_governance_manifest.json`
- `registry_hash_chain.ndjson`

Retention is explicit metadata, not a local filesystem enforcement mechanism.
The manifest says deletion requires human review, successor governance pack,
and recorded rationale.

## UI / Platform Impact

CLI-only. No API route or frontend surface changes.

## Observability

The governance manifest records owner, retention, artifact hashes, final chain
hash, and family evidence. Harness story, decision, matrix, and trace records
capture the high-risk methodology change.

## Alternatives Considered

1. Move directly to managed Postgres. Deferred because deployment ownership,
   migrations, credentials, and retention enforcement need a separate platform
   story.
2. Use manifest-only hashes. Rejected because per-row chain evidence gives a
   stronger tamper signal and supports linking future packs.
3. Make SQLite append-only. Deferred because local SQLite remains working
   storage; immutable evidence belongs in exported artifacts until managed
   storage is selected.
