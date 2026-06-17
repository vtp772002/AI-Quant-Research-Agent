# US-001 Core AI Quant Research Workflow

## Status

implemented

## Lane

normal

## Product Contract

The repository provides a runnable Python MVP for the AI Quant Research Agent:
configured data loading, factor construction, signal construction, long-short
backtesting, quantitative metrics, and automated Markdown report generation.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- A CLI can run the default configuration end to end.
- The system computes at least 20 reusable factors.
- The signal layer supports positive and negative factor exposures.
- The backtest calculates IC, Sharpe ratio, max drawdown, turnover, and total
  return across train, test, and full periods.
- The report layer writes a research summary with hypothesis, methodology,
  results, limitations, and next experiments.
- Unit tests cover data loading, factor generation, and the research workflow.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no application database in v1; experiment rows are appended to CSV.
- Domain rules: market data must use a `date, symbol` MultiIndex and OHLCV
  columns before entering factor/backtest code.
- UI surfaces: CLI and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `python -m pytest` covers data, factors, and workflow. |
| Integration | Default CLI run creates report and experiment CSV from config. |
| E2E | Not applicable; there is no browser/user UI in v1. |
| Platform | CLI smoke via `python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

This story converts the empty Harness repository into a concrete product
repository and adds product contract documentation.

## Evidence

- `.venv/bin/python -m pytest`: 3 tests passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated `reports/sample_research_report.md` and `results/experiments.csv`.
