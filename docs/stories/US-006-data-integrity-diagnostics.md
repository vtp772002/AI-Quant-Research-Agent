# US-006 Data Integrity Diagnostics

## Status

implemented

## Lane

normal

## Product Contract

The research workflow evaluates market data integrity before interpreting
backtest results. Reports and CLI JSON make data source assumptions, panel
coverage, and institutional-readiness gaps explicit.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config can declare whether a data source is point-in-time,
  survivorship-bias-free, and institutional-grade for corporate actions.
- The workflow computes a data integrity report after loading market data.
- Diagnostics include requested/observed symbols, row/date counts, duplicate
  index rows, missing symbols, per-symbol coverage, zero-volume rows,
  non-positive price rows, stale prices, and extreme returns.
- Synthetic and Yahoo demo sources produce explicit non-institutional warnings.
- Markdown reports include a `Data Integrity` section before performance
  interpretation.
- CLI JSON exposes structured data integrity diagnostics.
- Tests cover data integrity reporting and report output.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml`;
  compatibility: `python -m src.main --config configs/base.yaml`.
- Queries: none.
- API: no network API in v1.
- Tables: no database; data integrity is report/JSON evidence.
- Domain rules: diagnostics warn about institutional-readiness gaps but do not
  transform demo data into survivorship-safe point-in-time data.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers integrity diagnostics and workflow output. |
| Integration | Default CLI writes `Data Integrity` into generated report and JSON. |
| E2E | Not applicable; there is no browser/user UI in v1. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 4 tests passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/base.yaml --json`: generated structured `data_integrity` diagnostics and refreshed `reports/sample_research_report.md`.
- `.venv/bin/python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json`: generated structured `data_integrity` diagnostics and refreshed `reports/yahoo_nasdaq_research_report.md`.
- Synthetic and Yahoo reports include `Data Integrity` sections with point-in-time, survivorship, and corporate-action readiness warnings.
