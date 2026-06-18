# Design

## Domain Model

`ManagedRegistryDeployment` describes the local dry-run deployment bundle:

- `deployment_manifest.json`
- `postgres_apply_plan.sql`
- `object_lock_inventory.ndjson`
- copied object artifacts under `object_store/`

`ManagedRegistryVerification` verifies that the manifest, copied objects, and
inventory still match.

## Application Flow

Stage:

1. Verify the source governance pack with `verify_registry_governance_pack`.
2. Read the source governance manifest.
3. Copy governance artifacts into `object_store/<prefix>/`.
4. Write object-lock inventory records for every copied object.
5. Write a Postgres apply plan that includes migration/review comments and the
   existing generated upsert SQL.
6. Write a deployment manifest with source governance hash, owner, retention,
   adapter mode, object inventory hash, and credential/network checks.

Verify:

1. Load `deployment_manifest.json`.
2. Confirm adapter schema/version.
3. Recompute manifest artifact hashes.
4. Recompute object artifact hashes from inventory.
5. Fail if any expected local object is missing or changed.

## Interface Contract

```bash
python -m quant_research_agent.main \
  --stage-managed-registry results/managed_registry_deployment \
  --registry-governance-dir results/registry_export \
  --managed-registry-owner research-ops \
  --managed-registry-retention-days 730 \
  --managed-registry-object-prefix research/registry
```

```bash
python -m quant_research_agent.main \
  --verify-managed-registry results/managed_registry_deployment
```

The staging command exits non-zero if the source governance pack is invalid.
The verify command exits non-zero if the staged bundle is missing or tampered.

## Data Model

No database schema migration. The Postgres apply plan is a local SQL artifact,
not an applied migration.

Object-lock metadata is represented as NDJSON inventory rows:

- object key;
- local path;
- SHA-256;
- retention days;
- retain-until timestamp;
- legal-hold flag;
- source artifact name.

## UI / Platform Impact

CLI-only. No API route or frontend surface change.

## Observability

The deployment manifest records adapter mode, owner, source governance hash,
object-lock metadata, local object hashes, and explicit checks showing that no
credentials or network calls were used.

## Alternatives Considered

1. Connect to live Postgres. Rejected for this phase because the goal requires a
   deterministic adapter without credentials.
2. Only document the deployment. Rejected because the next phase needs an
   executable contract and verifier, not prose.
3. Reuse the governance manifest as the deployment manifest. Rejected because
   deployment staging adds object keys, retention policy, and Postgres apply
   plan metadata that do not belong in the source governance pack.
