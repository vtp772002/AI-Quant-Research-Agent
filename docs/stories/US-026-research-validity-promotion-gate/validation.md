# Validation

## Proof Strategy

The story is complete when configuration parsing is strict, holdout observations
are disjoint from validation evidence, the validity evaluator applies
Benjamini-Hochberg correction across the full within-run candidate family, all
artifact surfaces expose the evidence, checked-in demos run deterministically,
and the full pytest suite plus runtime checks pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Config parsing, strict booleans/numerics, p-values, Benjamini-Hochberg q-values, verdict branches, disabled-gate behavior. |
| Integration | Backtest split isolation, evaluator validity payload, report section, reproducibility manifest, workflow JSON, experiment CSV columns. |
| E2E | CLI smoke runs for base, point-in-time synthetic, institutional snapshot, and Yahoo demo configs. |
| Platform | Full pytest suite, compileall, pip dependency check, diff whitespace check, Harness story verification. |
| Performance | Not applicable; the gate reuses completed backtest outputs and small candidate tables. |
| Logs/Audit | Harness story, decision, matrix, and trace records capture methodology and proof. |

## Fixtures

- Deterministic synthetic market panel and signals in workflow tests.
- Checked-in demo configs:
  - `configs/base.yaml`
  - `configs/point_in_time_synthetic_demo.yaml`
  - `configs/institutional_snapshot_demo.yaml`
  - `configs/yahoo_nasdaq_demo.yaml`
- Generated sample reports under `reports/`.
- Reproducibility manifests under `results/runs/`.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_validity.py tests/test_workflow.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
/Users/phamtoan/Developer/AI-Quant-Research-Agent/scripts/bin/harness-cli story verify US-026
```

## Acceptance Evidence

Pre-closeout evidence recorded during implementation:

- Full suite passed after validity report/manifest/CSV integration: 111/111.
- Deterministic CLI smokes emitted enabled validity gates and advisory `REJECT`
  verdicts for base, point-in-time synthetic, institutional snapshot, and Yahoo
  demo configs.
- Regenerated sample reports include `Research Validity Gate`, `Verdict:
  REJECT`, and FDR q-value evidence.

Final closeout evidence is recorded in the Harness story row after the Task 8
verification pass.
