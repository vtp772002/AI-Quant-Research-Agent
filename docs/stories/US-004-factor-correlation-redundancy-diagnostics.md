# US-004 Factor Correlation And Redundancy Diagnostics

## Status

implemented

## Lane

normal

## Product Contract

The research workflow diagnoses selected agent and baseline factor exposures
before interpreting backtest results, so redundant or sparse factors are visible
in the generated report and CLI JSON output.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- The workflow identifies the unique factor exposures configured for the agent
  signal and non-random baselines.
- Diagnostics report factor observations, coverage, and missing rate.
- Diagnostics flag selected factor pairs with high absolute Spearman
  correlation.
- The Markdown report includes a `Factor Diagnostics` section.
- The CLI JSON output includes structured factor diagnostics.
- Tests cover diagnostics generation, report output, and redundant-pair
  detection.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database change; diagnostics are report/JSON evidence, not
  experiment-row metrics.
- Domain rules: diagnostics use Spearman correlation because the signal layer
  uses cross-sectional rank exposures.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers diagnostics and redundant-pair detection. |
| Integration | Default CLI writes `Factor Diagnostics` into the generated report. |
| E2E | Not applicable; there is no browser/user UI in v1. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 3 tests passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated structured factor diagnostics and refreshed `reports/sample_research_report.md`.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated structured factor diagnostics and refreshed `reports/yahoo_nasdaq_research_report.md`.
- `reports/sample_research_report.md` includes `Factor Diagnostics` and flags `momentum_20d` / `drawdown_20d` above the default absolute Spearman threshold.
