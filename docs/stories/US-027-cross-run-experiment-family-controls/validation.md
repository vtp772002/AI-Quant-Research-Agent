# Validation

## Proof Strategy

US-027 is complete when family metadata persists to manifests and registry
rows, family comparison applies cross-run Benjamini-Hochberg correction, CLI
Markdown/JSON outputs are deterministic, docs capture methodology limits, and
the full suite plus runtime checks pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Family config parsing, invalid selection policies, p-value extraction, BH q-values, verdict branches, warnings. |
| Integration | Manifest family metadata, registry migration, registry row fields, CLI JSON/Markdown output. |
| E2E | CLI run writes family metadata and `--compare-family` reads generated manifests. |
| Platform | Full pytest, compileall, pip check, diff check, Harness story verification. |
| Performance | Not applicable; comparison reads small manifest files. |
| Logs/Audit | Harness story, decision, matrix, and trace records. |

## Fixtures

- Synthetic manifests in `tests/test_experiment_family.py`.
- CLI E2E temporary config with `experiment.family`.
- Checked-in demo configs with stable family metadata.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py tests/test_workflow.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-027
```

## Acceptance Evidence

Final closeout evidence is recorded in the Harness story row after full
verification.
