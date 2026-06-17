# US-015 Run Comparison Over Reproducibility Manifests

## Status

implemented

## Lane

normal

## Product Contract

Researchers can compare previously generated reproducibility manifests from a
single run bundle or a `results/runs` directory, rank runs by a selected
test-period metric, and export the comparison as Markdown or JSON.

## Relevant Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`

## Acceptance Criteria

- CLI accepts `--compare-runs` with either a single `manifest.json` path or a
  directory containing run bundles.
- CLI supports ranking by Sharpe, total return, IC mean, max drawdown, average
  total cost, or average turnover.
- Comparison output includes run id, experiment, data source, dataset id,
  config hash, code commit, dirty flag, test metrics, observed symbol count, and
  manifest path.
- Lower-is-better metrics rank ascending; return and quality metrics rank
  descending.
- JSON output is machine-readable and Markdown output is human-readable.
- Optional `--limit` restricts returned ranked rows without changing discovered
  run count.
- Optional `--output` writes the rendered comparison to disk.
- Output warns when compared runs use different config hashes, git commits,
  dirty worktrees, data sources, or snapshot dataset ids.

## Design Notes

- Commands: `python -m quant_research_agent.main --compare-runs results/runs`.
- Queries: local manifest file discovery under `results/runs/*/manifest.json`.
- API: no API endpoint in this story.
- Tables: no database schema change.
- Domain rules: comparisons are provenance-aware summaries, not investment
  recommendations or statistical proof of alpha.
- UI surfaces: CLI Markdown and CLI JSON.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-015 --unit 1 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | `tests/test_run_comparison.py` covers ranking, warnings, single-manifest input, invalid metrics, JSON conversion, and Markdown rendering. |
| Integration | CLI test calls `main()` with `--compare-runs`, `--json`, `--limit`, and `--output`. |
| E2E | Full pytest suite remains green. |
| Platform | CLI smoke against existing `results/runs` manifests passes with `PYTHONPATH=src`. |
| Release | Not applicable in v1. |

## Harness Delta

No Harness process change expected for this story.

## Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_run_comparison.py -q` passed 5/5.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 16/16.
- `git diff --check` passed.
- `PYTHONPATH=src python -m quant_research_agent.main --compare-runs results/runs --json --limit 3` passed and discovered 5 manifests.
- `PYTHONPATH=src python -m quant_research_agent.main --compare-runs results/runs --comparison-metric average_total_cost --limit 2 --output results/run_comparison.md` passed; the generated smoke artifact was removed from the working tree.
