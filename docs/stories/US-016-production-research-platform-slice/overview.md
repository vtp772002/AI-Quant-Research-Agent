# Overview

## Current Behavior

The project is a Python CLI research prototype that can run deterministic
backtests, write Markdown reports, append CSV experiment rows, and emit
reproducibility manifests. It has no service surface, queryable run registry,
as-of signal interface, deployment scaffold, or automated CI contract.

## Target Behavior

The project should support a first production-research-platform slice:

- CLI runs still work as before.
- Each run is also persisted into a queryable local experiment registry.
- Internal service endpoints expose health, run execution, run lookup, report
  lookup, and as-of signal generation.
- As-of signal generation must use only data available on or before the
  requested date.
- Local deployment and CI scaffolding must exist for the API and validation
  commands.

## Affected Users

- Quant researcher running internal experiments.
- Agent or operator comparing reproducible runs.
- Internal service consumer requesting latest research signals.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Live trading.
- Broker or exchange integration.
- Order management, fills, reconciliation, or kill switch behavior.
- Multi-user auth, authorization, billing, or SaaS packaging.
- Replacing CSV snapshot fixtures with a commercial market-data vendor.
