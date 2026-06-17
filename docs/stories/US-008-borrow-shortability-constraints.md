# US-008 Borrow Costs And Shortability Constraints

## Status

implemented

## Lane

normal

## Product Contract

The long-short backtest accounts for short-leg feasibility by enforcing a
configured shortable universe and charging annualized borrow fees on short
exposure.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports `experiment.shorting.borrow_fee_bps`.
- Config supports optional `experiment.shorting.shortable_symbols`.
- Short portfolio construction excludes non-shortable symbols from the short
  leg when a shortable universe is configured.
- Borrow cost is charged on short exposure for the configured holding period.
- Borrow cost contributes to total strategy cost and all split/walk-forward
  metrics.
- Reports include borrow fee and shortable universe metadata.
- CLI JSON exposes shorting configuration metadata and borrow cost metrics.
- Experiment CSV includes borrow cost metrics.
- E2E test verifies borrow cost output through the CLI.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database; `results/experiments.csv` records borrow cost metrics
  as strategy metrics.
- Domain rules: shortability constraints affect only short candidates. Borrow
  costs are research approximations and do not represent actual locate records.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers borrow cost and shortable output. |
| Integration | Default CLI writes borrow metadata and cost metrics into report and CSV. |
| E2E | `tests/test_cli_e2e.py` verifies CLI JSON/report/CSV borrow cost outputs. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 5 tests passed, including CLI E2E coverage.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated borrow metadata and positive borrow cost metrics.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated borrow metadata and positive borrow cost metrics for the Yahoo demo.
- `reports/sample_research_report.md` and `reports/yahoo_nasdaq_research_report.md` include borrow fee, shortable universe, and average borrow cost.
- `results/experiments.csv` includes `test_average_borrow_cost` and `full_average_borrow_cost`.
