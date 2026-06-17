# US-003 Walk-Forward Validation

## Status

implemented

## Lane

normal

## Product Contract

The research workflow supports configured walk-forward validation so an agent
signal and its baselines can be judged across multiple chronological test
windows instead of relying only on one train/test split.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- The experiment config can request walk-forward validation under
  `experiment.validation.walk_forward`.
- The agent signal and configured baselines use the same walk-forward window
  settings.
- The Markdown report includes agent-signal window metrics and a strategy-level
  walk-forward stability comparison.
- The experiment CSV includes rows keyed by experiment, source, strategy, and
  window.
- Tests cover walk-forward execution, report output, and CSV rows.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database; `results/experiments.csv` records full-sample and
  walk-forward strategy rows.
- Domain rules: walk-forward windows are chronological expanding-window tests
  computed from the same return, IC, and turnover series as the main backtest.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers walk-forward execution and outputs. |
| Integration | Default CLI writes walk-forward sections and CSV rows. |
| E2E | Not applicable; there is no browser/user UI in v1. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 3 tests passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated 3 agent-signal walk-forward windows and refreshed `reports/sample_research_report.md`.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated 3 Yahoo demo agent-signal walk-forward windows and refreshed `reports/yahoo_nasdaq_research_report.md`.
- `results/experiments.csv` contains `full_sample`, `wf_01`, `wf_02`, and `wf_03` rows for each configured strategy in both experiments.
