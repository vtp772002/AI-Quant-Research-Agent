# Design

## Domain Model

- Batch run: a set of config paths, successful workflow runs, per-config
  failures, and comparison artifacts.
- Registry export: an offline snapshot of local registry records plus a manifest
  and reviewable Postgres handoff SQL.
- Vendor snapshot: a commercial data file drop that must satisfy the same OHLCV
  columns as snapshot research data.
- Alpha template: a draft experiment configuration extracted heuristically from
  paper/blog text.
- Execution simulation: an as-of order plan derived from target weights and
  participation limits, with no broker side effects.

## Application Flow

```text
config paths
  -> run existing workflow for each config
  -> record successes/failures
  -> compare generated manifests
  -> write batch summary and comparison artifacts
```

```text
sqlite registry
  -> query local records
  -> write NDJSON records
  -> write export manifest
  -> write Postgres handoff SQL
```

```text
paper/blog text
  -> heuristic keyword extraction
  -> draft factors and holding period
  -> YAML experiment template
```

```text
as-of signal
  -> target weights
  -> participation gates
  -> simulated schedule/block decisions
```

## Interface Contract

CLI additions:

- `--run-batch <config...>`
- `--batch-output-dir <path>`
- `--export-registry <dir>`
- `--paper-to-alpha <path>`
- `--template-output <path>`
- `--simulate-execution`
- `--execution-output <path>`
- `--max-participation <float>`

Data source addition:

- `data.source: vendor_snapshot` uses `data.snapshot.path` and the existing
  OHLCV columns.

## Data Model

No existing database schema is changed. Registry export writes:

- `experiment_runs.ndjson`
- `registry_export_manifest.json`
- `postgres_upsert_experiment_runs.sql`

## Safety Boundary

Vendor snapshot ingestion is a file-drop adapter. Execution simulation is a
broker-free feasibility model. Neither path performs network calls, manages
secrets, places orders, reserves locates, or reconciles fills.
