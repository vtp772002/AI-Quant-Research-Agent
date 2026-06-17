# US-013 Capacity And Concentration Diagnostics

## Status

implemented

## Lane

normal

## Product Contract

The research workflow computes capacity and concentration diagnostics so a
strategy can be evaluated against portfolio concentration, market-impact, and
trade-participation constraints across configured target notionals.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports `experiment.capacity.notionals`.
- Config supports `experiment.capacity.max_trade_participation`.
- Config supports `experiment.capacity.max_position_weight`.
- Capacity diagnostics compute max single-name weight.
- Capacity diagnostics compute average and minimum effective position count.
- Capacity diagnostics compute gross exposure summary.
- Capacity diagnostics count position weight breaches.
- Capacity curve reruns the agent signal across configured notionals.
- Capacity curve reports test Sharpe, test return, total cost, impact cost,
  average participation, max participation, and breach count.
- Capacity curve estimates max passing notional under positive-Sharpe and
  participation gates.
- Capacity variants use the same shorting and locate-history constraints as
  the primary backtest.
- CLI JSON exposes concentration and capacity curve diagnostics.
- Markdown reports include a Capacity Diagnostics section.
- Workflow and CLI E2E tests cover capacity diagnostics.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml`.
- Queries: none.
- API: no external execution venue API in this story.
- Tables: no database; capacity diagnostics are emitted in CLI JSON and
  generated Markdown reports.
- Domain rules: capacity curves reuse the same signal, train/test split,
  shorting constraints, locate availability, transaction costs, and borrow
  fees. Market impact is still the existing average-dollar-volume model, so
  capacity is a research approximation rather than an order-book simulation.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers workflow capacity diagnostics. |
| Integration | Institutional snapshot demo CLI writes capacity JSON and report sections. |
| E2E | `tests/test_cli_e2e.py` verifies capacity JSON and report output. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 8 tests passed, including workflow and CLI E2E capacity coverage.
- Workflow test verifies concentration metrics, three capacity curve points, and deterministic participation breaches.
- CLI E2E verifies capacity JSON, capacity curve length, participation breach count, and `Capacity Diagnostics` report section.
- `configs/base.yaml`, `configs/yahoo_nasdaq_demo.yaml`, `configs/point_in_time_synthetic_demo.yaml`, and `configs/institutional_snapshot_demo.yaml` each configure four capacity notionals.
- Institutional snapshot CLI smoke generated 4 capacity points, max single-name weight 100.00%, one concentration warning, and estimated passing capacity of 25,000,000 notional.
- Base CLI smoke generated 4 capacity points and estimated passing capacity of 1,000,000 notional.
- Yahoo CLI smoke generated 4 capacity points and flagged capacity warnings without a passing configured notional.
- Point-in-time synthetic CLI smoke generated 4 capacity points and estimated passing capacity of 10,000,000 notional.
