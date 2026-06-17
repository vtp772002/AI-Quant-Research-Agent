# US-002 Real-Data Config And Baseline Comparison

## Status

implemented

## Lane

normal

## Product Contract

The research workflow supports baseline strategies and includes a Yahoo Finance
demo configuration so an experiment can be compared against simple factor and
random baselines before treating the agent signal as useful.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- The default synthetic config defines baseline strategies.
- A Yahoo Finance config exists for a Nasdaq-style large-cap universe.
- The evaluator backtests configured baselines with the same data, split,
  rebalance, quantile, and transaction cost settings as the agent signal.
- The Markdown report includes a baseline comparison table using test-period
  metrics.
- The experiment CSV writes one row per strategy and upserts repeated runs by
  experiment, source, and strategy.
- Tests cover baseline execution and report/CSV output.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  real-data demo: `python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml`.
- Queries: none.
- API: no application API; Yahoo Finance is reached only when the user selects
  `data.source: yahoo`.
- Tables: no database; `results/experiments.csv` records strategy rows.
- Domain rules: baselines must use the same backtest settings as the agent
  signal to keep comparisons fair.
- UI surfaces: CLI and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers baseline execution and output. |
| Integration | Default CLI writes baseline rows to report and CSV. |
| E2E | Not applicable; there is no browser/user UI in v1. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 3 tests passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated synthetic report with baseline comparison.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated Yahoo/Nasdaq report with baseline comparison.
