# US-012 Locate And Borrow Availability History

## Status

implemented

## Lane

normal

## Product Contract

The long-short research workflow supports date-aware locate and borrow
availability history so short-leg feasibility can vary by date and symbol
instead of relying only on a static shortable list and a constant borrow fee.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports `experiment.shorting.locate_history_path`.
- Locate history CSV supports `date,symbol,shortable,borrow_fee_bps`.
- Locate history CSV supports optional `available_quantity`.
- Duplicate date-symbol locate rows fail fast.
- Missing locate rows are treated as not shortable.
- `available_quantity <= 0` rows are treated as not shortable.
- Backtest short candidates are intersected with date-aware locate availability.
- Borrow cost uses date-symbol borrow fees from locate history when configured.
- Fallback `experiment.shorting.borrow_fee_bps` remains supported.
- Baselines, stress tests, and robustness variants use the same locate history.
- CLI JSON exposes locate history summary and warnings.
- Markdown reports include a Borrow Availability section.
- Experiment CSV records the locate history source path.
- A demo locate history CSV is included.
- Unit/workflow/E2E tests cover date-aware locate enforcement and output.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml`.
- Queries: none.
- API: no external securities-lending API in this story. CSV is the local
  adapter surface for future vendor locate integrations.
- Tables: no database; locate summary is emitted in CLI JSON, Markdown reports,
  and experiment CSV rows.
- Domain rules: missing locate rows are conservative and not shortable. Static
  `shortable_symbols` and date-aware locate availability both apply when both
  are configured. Borrow fee history affects borrow cost but does not model
  intraday recalls, partial fills, broker allocation queues, or actual locate
  entitlements.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers workflow and CLI locate history behavior. |
| Integration | Institutional snapshot demo CLI writes locate summary and dynamic borrow costs. |
| E2E | `tests/test_cli_e2e.py` verifies locate JSON, report, and experiment CSV output. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 8 tests passed, including workflow and CLI E2E locate-history coverage.
- Workflow test verifies negative positions only occur on date-symbol rows marked shortable in the locate history.
- CLI E2E verifies locate history path, unavailable rows, hard-to-borrow rows, Borrow Availability report section, and experiment CSV `locate_history`.
- `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json`: generated 6,264 locate rows, 100.00% coverage, 1,698 unavailable rows, 783 hard-to-borrow rows, and positive dynamic borrow cost.
- Base, Yahoo, and point-in-time synthetic CLI smokes still pass with `borrow_availability: null`.
- `configs/institutional_snapshot_demo.yaml` uses `data/golden/borrow_availability_demo.csv`.
