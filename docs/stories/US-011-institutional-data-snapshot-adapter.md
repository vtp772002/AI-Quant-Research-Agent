# US-011 Institutional Data Snapshot Adapter

## Status

implemented

## Lane

normal

## Product Contract

The research workflow supports reproducible CSV market-data snapshots with a
manifest that validates dataset provenance before factors, backtests, reports,
and experiment rows are produced.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- Config supports `data.source: csv_snapshot`.
- Config supports `data.snapshot.path`.
- Config supports `data.snapshot.manifest_path`.
- Config supports `data.snapshot.require_manifest_hash`.
- CSV snapshot loader parses `date,symbol,open,high,low,close,adj_close,volume`.
- Snapshot loader filters to the resolved universe and requested date range.
- Manifest validation computes SHA-256 for the data file.
- Hash mismatch fails fast when `require_manifest_hash` is enabled.
- Manifest validation exposes row-count, symbol-set, and date-range checks.
- Manifest institutional flags can satisfy point-in-time, survivorship-free,
  and corporate-action-adjusted data integrity checks.
- CLI JSON exposes snapshot provenance and validation flags.
- Markdown reports expose snapshot dataset, vendor, as-of, manifest, and
  validation flags.
- Experiment CSV records dataset id, vendor, and as-of fields.
- A golden snapshot demo config and fixture are included.
- Unit and CLI E2E tests cover snapshot loading and provenance validation.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml`.
- Queries: none.
- API: no external vendor API in this story. The snapshot adapter is the
  reproducible handoff boundary that future vendor integrations can write into.
- Tables: no database; snapshot provenance is emitted in CLI JSON, Markdown
  reports, and experiment CSV rows.
- Domain rules: the manifest describes the loaded research panel after universe
  filtering. A hash mismatch is fatal when strict hash validation is enabled;
  other manifest mismatches are reported as provenance warnings.
- UI surfaces: CLI JSON output and generated Markdown report.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers CSV snapshot loading and manifest provenance. |
| Integration | Snapshot demo CLI writes report/JSON with validated provenance. |
| E2E | `tests/test_cli_e2e.py` runs the CLI against a generated snapshot fixture. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 8 tests passed, including snapshot loader unit coverage and snapshot CLI E2E.
- `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json`: generated `institutional-golden-demo-v1` provenance with valid hash, row count, symbol set, and date range.
- Snapshot demo produced 6,264 panel rows, 8 symbols, point-in-time universe true, survivorship-bias-free true, and corporate-action-adjusted true.
- `reports/institutional_snapshot_research_report.md` includes snapshot dataset, vendor, as-of, manifest path, and validation flags.
