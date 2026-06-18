# Design

## Domain Model

`LockedHoldoutConfig` is nested under
`experiment.validation.research_validity.locked_holdout`:

- `enabled`: fail-closed validation gate.
- `manifest_path`: YAML manifest describing the locked holdout.
- `require_manifest_hash`: require manifest `content_sha256` to match the
  current market data file when a file-backed snapshot is available.

`LockedHoldoutEvidence` records the realized holdout boundary and manifest
validation result. It is immutable once attached to `ResearchRunResult`.

## Application Flow

1. Parse optional locked-holdout config.
2. Run the existing workflow and backtest.
3. After `holdout_start` is known, validate the manifest against the realized
   market-data holdout slice.
4. Fail closed on missing manifest, hash mismatch, date mismatch, symbol
   mismatch, or required row-count mismatch.
5. Attach evidence to the workflow result.
6. Write evidence into CLI payload, reproducibility manifest, report text, and
   registry metrics.

## Interface Contract

Example config:

```yaml
experiment:
  validation:
    research_validity:
      enabled: true
      locked_holdout:
        enabled: true
        manifest_path: data/golden/locked_holdout_manifest.yaml
        require_manifest_hash: true
```

Example manifest:

```yaml
schema_version: locked_holdout_v1
dataset_id: institutional-holdout-demo-v1
content_sha256: "<sha256 of locked data file>"
start: "2022-08-01"
end: "2022-12-30"
symbols: [AAA, BBB, CCC]
row_count: 315
minimum_row_count: 250
owner: research-ops
purpose: final_promotion_holdout
```

## Data Model

No SQLite schema migration is required. Locked holdout evidence is stored inside
manifest `metrics.research_validity.locked_holdout` and therefore enters the
existing registry JSON metrics payload.

## UI / Platform Impact

CLI/report only. No API route changes are required for the first slice because
existing run payloads expose the new evidence.

## Observability

The Markdown report includes a `Locked Holdout` section in the Research Validity
Gate block. CLI JSON and reproducibility manifests include machine-readable
evidence.

Harness story, decision, matrix, and trace records capture proof.

## Alternatives Considered

1. Create a separate holdout data loader. Deferred because the first valuable
   boundary is verification of realized holdout provenance, not a new storage
   system.
2. Treat locked holdout mismatches as warnings. Rejected because promotion
   evidence must fail closed when the locked boundary is configured.
3. Require managed storage immediately. Deferred until US-030; US-029 remains
   deterministic and local.
