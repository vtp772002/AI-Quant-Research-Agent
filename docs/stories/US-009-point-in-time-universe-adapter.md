# US-009 Point-In-Time Universe Adapter

## Status

implemented

## Lane

normal

## Product Contract

The research workflow supports a point-in-time universe membership adapter so
market data can be filtered to symbols active during each membership interval
before factors and backtests are computed.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports `data.universe_provider.kind`.
- Static universe behavior remains backward-compatible.
- CSV universe provider supports `symbol,start,end` membership columns.
- CSV provider resolves active symbols for the experiment date range.
- Market data rows outside each symbol's membership interval are removed before
  factor generation and backtesting.
- CLI JSON exposes universe source, symbol count, membership rows, and
  point-in-time/survivorship-safe flags.
- Reports show universe source and membership row count in `Data Integrity`.
- A demo point-in-time config and membership CSV are included.
- E2E test exercises the CSV universe provider through the CLI.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml`.
- Queries: none.
- API: no network API in v1; CSV is the local adapter surface for future vendor
  integration.
- Tables: no database; membership CSV is a config-side data input.
- Domain rules: CSV membership with `symbol,start,end` is treated as
  point-in-time and survivorship-bias-free for adapter purposes, but corporate
  action quality still depends on the market data source.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers CSV membership resolution and filtering. |
| Integration | Point-in-time demo CLI writes report/JSON with CSV universe metadata. |
| E2E | `tests/test_cli_e2e.py` runs the CLI with a temp CSV universe provider. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 6 tests passed, including CSV universe unit coverage and CLI E2E.
- `.venv/bin/python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml --json`: generated a report using `csv:configs/universe_membership_demo.csv` with 20 resolved symbols and 20 membership rows.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: static universe smoke passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: Yahoo/static universe smoke passed.
- `reports/point_in_time_synthetic_research_report.md` includes `Universe source`, `Membership rows`, and point-in-time/survivorship flags.
