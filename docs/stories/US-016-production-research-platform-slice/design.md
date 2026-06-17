# Design

## Domain Model

- Experiment run: reproducibility manifest plus key query fields such as run id,
  experiment name, data source, dataset id, config hash, code version, report
  path, and test metrics.
- As-of signal: signal rows for one decision date, including score, rank,
  target weight, risk status, reason, data timestamp, and model/config version.

## Application Flow

CLI and API should share one run orchestration function:

```text
config path
  -> parse config
  -> create run context
  -> run research workflow
  -> write report, CSV rows, reproducibility pack
  -> persist registry row
  -> return JSON-safe payload
```

As-of signal generation uses the same data, universe, factors, and configured
signal as the backtest workflow, but truncates market data to the requested
date and never computes forward returns.

## Interface Contract

- `GET /health`
- `GET /metrics`
- `POST /experiments/run`
- `GET /experiments/{run_id}`
- `GET /reports/{run_id}`
- `GET /signals/latest`
- `GET /signals/as-of`

The API is an internal service interface for research automation, not a public
investment-advice API.

## Data Model

The first queryable registry uses SQLite at `results/experiments.sqlite` by
default. It is intentionally local and simple, but its row shape mirrors the
fields a later PostgreSQL registry should keep.

Table:

- `experiment_runs`

Retention is manual in this slice. Immutable artifact storage is a later phase.

## UI / Platform Impact

No dashboard UI is added in this slice. The platform impact is Docker, compose,
environment example, and GitHub Actions validation.

## Observability

The service emits one structured JSON log line per request with timestamp,
level, request id, action, duration, status code, and message. Audit-grade
trading logs are out of scope because this slice does not trade.

## Alternatives Considered

1. Jump directly to Postgres, Redis workers, and scheduler orchestration. This
   was deferred because the current codebase has no service layer yet and the
   smallest useful production step is to define stable application boundaries.
2. Add live broker integration. This was rejected for this slice because it
   requires risk, compliance, reconciliation, and key-management requirements
   that are not present in the repo.
