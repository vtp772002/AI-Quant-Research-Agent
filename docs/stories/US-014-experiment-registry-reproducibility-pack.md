# US-014 Experiment Registry And Reproducibility Pack

## Status

implemented

## Lane

normal

## Product Contract

Each CLI experiment run emits a reproducibility pack that identifies the run,
freezes the config, records code and data fingerprints, hashes generated
artifacts, and connects experiment CSV rows back to the run id and config hash.

## Relevant Product Docs

- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- CLI run creates a unique `run_id`.
- CLI JSON exposes run id, generated timestamp, manifest path, config hash, and
  code metadata.
- Config file SHA-256 is recorded.
- A frozen copy of the config is written into the run bundle.
- Git commit, branch, and dirty flag are recorded.
- Snapshot dataset hash is recorded when a snapshot source is configured.
- Locate-history hash is recorded when locate history is configured.
- Report and experiment CSV artifact hashes are recorded.
- Manifest JSON is written under `results/runs/<run_id>/manifest.json`.
- Markdown report includes a `Run Reproducibility` section.
- Experiment CSV rows include `run_id` and `config_sha256`.
- CLI E2E verifies manifest existence, frozen config, artifact hashes, and CSV
  run metadata.

## Design Notes

- Commands: `python -m quant_research_agent.main --config configs/base.yaml --json`.
- Queries: none.
- API: no external registry service in this story.
- Tables: `results/experiments.csv` records run id and config hash; per-run
  manifests are generated artifacts under `results/runs/`.
- Domain rules: run bundles are immutable-by-convention local artifacts. They
  are not a substitute for object-lock storage, signed manifests, or a managed
  experiment tracking service.
- UI surfaces: CLI JSON output, Markdown report, experiment CSV, and
  `manifest.json`.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `.venv/bin/python -m pytest` covers CLI reproducibility pack output. |
| Integration | Demo CLI runs write manifests and report reproducibility sections. |
| E2E | `tests/test_cli_e2e.py` verifies manifest hashes, frozen config, and CSV run metadata. |
| Platform | CLI smoke via `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected.

## Evidence

- `.venv/bin/python -m pytest`: 8 tests passed, including CLI E2E reproducibility pack coverage.
- CLI E2E verifies run id, config SHA-256, manifest JSON, frozen config, report hash, experiment CSV hash, locate-history hash, and snapshot hash.
- Base, Yahoo, point-in-time, and institutional snapshot CLI smokes generate `Run Reproducibility` report sections and per-run manifests under `results/runs/`.
- Institutional snapshot smoke manifest records config SHA-256, report hash, experiment CSV hash, snapshot content hash, and locate-history hash.
