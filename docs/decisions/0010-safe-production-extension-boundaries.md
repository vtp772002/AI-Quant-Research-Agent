# Safe Production Extension Boundaries

Date: 2026-06-17

## Status

Accepted

## Context

The repo now has a reusable CLI workflow, reproducibility manifests, a local
SQLite registry, run comparison, an internal API, and as-of signal generation.
The next requested roadmap spans scheduling, registry handoff, vendor data,
paper-to-alpha extraction, and execution simulation.

Several of those areas are high-risk if interpreted as live provider or broker
behavior. Direct vendor APIs require credential handling, entitlement review,
rate-limit behavior, provenance controls, and failure policy. Broker or paper
trading behavior requires risk gates, locate entitlements, order management,
fill reconciliation, kill switches, audit records, and operational incident
response.

## Decision

Implement the next production extension as deterministic, offline-safe
boundaries:

- Batch orchestration runs existing configs and writes local comparison
  artifacts.
- Registry export produces object-store style NDJSON plus reviewable Postgres
  handoff SQL, but does not manage a remote database.
- Vendor ingestion accepts validated vendor snapshot drops through the existing
  OHLCV snapshot boundary, but does not call live vendor APIs.
- Paper-to-alpha extraction emits draft experiment templates requiring human
  review.
- Execution simulation converts as-of target weights into a broker-free plan
  with participation gates, but does not route orders, reserve locates, or place
  trades.

## Alternatives Considered

1. Build live vendor API and broker integrations now. Rejected because the repo
   lacks the credential, entitlement, risk, and audit contracts required to do
   that safely.
2. Keep the roadmap as docs only. Rejected because deterministic offline
   vertical slices provide useful operating leverage without unsafe provider
   behavior.
3. Move directly to managed Postgres/object storage. Deferred until migrations,
   retention, deployment ownership, and auth requirements are specified.

## Consequences

Positive:

- The repo gains an operating loop without pretending to be a trading system.
- Future provider and broker stories have stable boundaries to extend.
- Validation remains deterministic and local.

Tradeoffs:

- Registry export is a handoff artifact, not a live remote registry.
- Vendor ingestion depends on snapshot drops rather than direct vendor APIs.
- Execution simulation is useful for feasibility review, not paper trading.

## Follow-Up

- Add managed Postgres/object-storage deployment only after ownership and
  migration rules are specified.
- Add live vendor APIs only after credential and entitlement contracts exist.
- Add paper-trading stories only after risk gates, reconciliation, and kill
  switch requirements are documented.
