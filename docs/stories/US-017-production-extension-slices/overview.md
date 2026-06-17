# Overview

## Current Behavior

The platform can run single research configs, persist reproducibility manifests,
query a local SQLite registry, generate as-of signals, compare runs, and expose
an internal API. The remaining production-readiness gaps are the operating loop
around those capabilities and safe boundaries for later provider and execution
work.

## Target Behavior

The repo should support six safe production extension slices:

- Scheduled-style batch orchestration for one or more configs.
- Trace-documentation alignment with the current Harness CLI.
- Offline registry export for object-store/Postgres handoff review.
- Vendor snapshot ingestion through the validated OHLCV boundary.
- Paper-to-alpha draft template extraction.
- Broker-free execution simulation with participation gates.

## Affected Users

- Quant researcher running repeatable daily research jobs.
- Operator exporting experiment history for a future managed registry.
- Researcher converting papers/blogs into experiment drafts.
- Research reviewer checking execution feasibility without broker behavior.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TRACE_SPEC.md`

## Non-Goals

- Live trading.
- Paper trading with a broker.
- Broker SDK integration.
- Live commercial vendor API calls.
- Credential, secret, entitlement, auth, or authorization management.
- Managed Postgres/object-storage deployment.
