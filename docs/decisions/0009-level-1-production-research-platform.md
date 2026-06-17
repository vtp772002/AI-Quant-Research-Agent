# Level 1 Production Research Platform Slice

Date: 2026-06-17

## Status

Accepted

## Context

The production-readiness review identified that the repository is a strong
research/backtesting prototype, but not a production trading system. Moving
directly to broker execution would require market-data contracts, hard risk
gates, secret management, compliance review, audit trails, reconciliation, and
incident response that are not specified in the repo.

## Decision

Treat the next implementation step as a Level 1 internal production research
platform slice. Add service, registry, as-of signal, deployment, and CI
boundaries while explicitly excluding paper trading and live trading behavior.

## Alternatives Considered

1. Build live trading first. Rejected because it would create unsafe execution
   behavior without broker, risk, compliance, and reconciliation contracts.
2. Build only documentation. Rejected because the repo can absorb a useful
   vertical slice now: queryable runs, service endpoints, and as-of signals.
3. Build full orchestration with Postgres, Redis workers, object storage, and a
   dashboard. Deferred because the current system needs stable application and
   interface boundaries first.

## Consequences

Positive:

- The CLI remains the core deterministic research workflow.
- API and registry surfaces become testable without live trading risk.
- Later Postgres/object-storage/orchestration work has a clear data contract.

Tradeoffs:

- SQLite is not the final system of record for a multi-user production
  deployment.
- The API is internal and unauthenticated in this slice.
- No order execution or broker integration is added.

## Follow-Up

- Add a real Postgres-backed registry when multi-user or remote deployment is
  required.
- Add scheduler/worker orchestration after the run API and registry stabilize.
- Add paper-trading stories before any live trading work.
