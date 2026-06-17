# US-010 Robustness And Overfit Diagnostics

## Status

implemented

## Lane

normal

## Product Contract

The research workflow computes robustness diagnostics that make overfit risk
and strategy fragility visible through bootstrap confidence intervals,
parameter sensitivity grids, and cost sensitivity grids.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports `experiment.robustness.bootstrap_iterations`.
- Config supports `experiment.robustness.bootstrap_seed`.
- Config supports parameter sensitivity grids for holding periods and
  portfolio quantiles.
- Config supports cost sensitivity multipliers applied to transaction,
  spread, impact, and borrow costs.
- Bootstrap diagnostics report test Sharpe and test IC confidence intervals.
- Bootstrap diagnostics report positive Sharpe and positive IC probabilities.
- Parameter sensitivity reruns the backtest across the configured grid.
- Cost sensitivity reruns the backtest across configured cost multipliers.
- CLI JSON exposes bootstrap, parameter sensitivity, and cost sensitivity
  diagnostics.
- Markdown reports include a robustness diagnostics section and interpretation.
- E2E test verifies robustness output through the CLI.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database; robustness diagnostics are included in CLI JSON and
  generated Markdown reports.
- Domain rules: bootstrap resamples test-period strategy returns and IC series.
  Parameter and cost sensitivity reruns reuse the same market data, signal, and
  chronological train/test split.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers workflow robustness diagnostics. |
| Integration | Default, Yahoo, and point-in-time demo CLIs write robustness JSON and reports. |
| E2E | `tests/test_cli_e2e.py` verifies CLI robustness JSON and report sections. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 6 tests passed, including workflow and CLI E2E robustness coverage.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated bootstrap diagnostics with 200 iterations, 9 parameter sensitivity variants, and 3 cost sensitivity variants.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated bootstrap diagnostics with 200 iterations, 9 parameter sensitivity variants, and 3 cost sensitivity variants.
- `.venv/bin/python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml --json`: generated bootstrap diagnostics with 200 iterations, 9 parameter sensitivity variants, and 3 cost sensitivity variants.
- `reports/sample_research_report.md`, `reports/yahoo_nasdaq_research_report.md`, and `reports/point_in_time_synthetic_research_report.md` include `Robustness Diagnostics`.
