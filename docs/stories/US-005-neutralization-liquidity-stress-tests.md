# US-005 Neutralization And Liquidity Stress Tests

## Status

implemented

## Lane

normal

## Product Contract

The research workflow can stress-test the agent signal under sector
neutralization and liquidity filtering without changing the primary signal
backtest. Stress-test variants use the same backtest settings, walk-forward
windows, and output surfaces as the agent signal.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports per-symbol sector metadata.
- Config can enable sector neutralization and liquidity-filter stress tests.
- Sector neutralization subtracts sector mean signal by rebalance date.
- Liquidity filtering removes assets below a configured cross-sectional
  `dollar_volume_20d` rank.
- Report includes a `Stress Tests` section comparing test-period metrics.
- CLI JSON exposes structured stress-test metrics.
- Experiment CSV records stress-test variants with the same full-sample and
  walk-forward rows as other strategies.
- Tests cover stress-test execution, report output, and CSV rows.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database; `results/experiments.csv` records stress-test rows as
  strategy variants.
- Domain rules: stress tests are diagnostics and do not alter the primary
  agent signal result.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers stress-test execution and outputs. |
| Integration | Default CLI writes `Stress Tests` into generated report and CSV. |
| E2E | Not applicable; there is no browser/user UI in v1. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 3 tests passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated `sector_neutral_signal`, `liquidity_top_80pct`, and `sector_neutral_liquidity_top_80pct` stress-test variants.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated the same stress-test variants for the Yahoo demo.
- `results/experiments.csv` contains `full_sample`, `wf_01`, `wf_02`, and `wf_03` rows for stress-test variants in both experiments.
