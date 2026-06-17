# US-007 Liquidity-Sensitive Transaction Cost And E2E Validation

## Status

implemented

## Lane

normal

## Product Contract

The research workflow models execution costs with base turnover cost, spread
cost, and liquidity-sensitive market impact. The CLI has an automated E2E test
that runs a complete synthetic experiment and verifies JSON, report, and CSV
outputs.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Backtest config supports `spread_cost_bps`, `market_impact_coefficient`, and
  `portfolio_notional`.
- All strategy variants use the same execution cost assumptions.
- Backtest results expose raw returns, net returns, cost components, and trade
  participation metrics.
- Split and walk-forward metrics include average base, spread, impact, total
  cost, cumulative cost, and participation diagnostics.
- Markdown reports include an `Execution Costs` section and cost columns in
  comparison tables.
- Experiment CSV records cost metrics for full-sample and walk-forward rows.
- CLI JSON includes cost metrics.
- E2E test runs `python -m quant_research_agent.main --config ... --json` and
  verifies report, JSON, and experiment rows.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database; `results/experiments.csv` records cost metrics as
  strategy metrics.
- Domain rules: market impact uses trade notional divided by rolling 20-day
  average dollar volume. This is a research approximation, not a broker-grade
  execution simulator.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers cost metrics and workflow output. |
| Integration | Default CLI writes `Execution Costs` into generated report and CSV. |
| E2E | `tests/test_cli_e2e.py` runs the CLI with a temp config and verifies JSON/report/CSV outputs. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 5 tests passed, including `tests/test_cli_e2e.py`.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated execution cost metrics with base, spread, impact, and participation diagnostics.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated execution cost metrics for the Yahoo demo.
- `reports/sample_research_report.md` and `reports/yahoo_nasdaq_research_report.md` include `Execution Costs`.
- `results/experiments.csv` includes cost metric columns such as `test_average_total_cost`, `test_average_impact_cost`, and `test_max_trade_participation`.
