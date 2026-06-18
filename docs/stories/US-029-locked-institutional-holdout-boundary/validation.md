# Validation

## Proof Strategy

The story is complete when a config can require a locked holdout manifest,
successful runs emit locked holdout evidence, mismatch cases fail closed before
promotion artifacts are accepted, and the full validation ladder passes.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Parse locked holdout config; validate manifest success, hash mismatch, date mismatch, symbol mismatch, row-count mismatch. |
| Integration | Workflow emits locked holdout evidence in payload and reproducibility manifest. |
| E2E | CLI run with locked holdout config completes and writes report/manifest evidence. |
| Platform | Local file-backed deterministic manifest validation. |
| Performance | No separate benchmark; validation scans existing in-memory holdout slice. |
| Logs/Audit | Harness story, decision, matrix, and trace records. |

## Fixtures

- Synthetic temporary config and market-data CSV/manifest fixtures in tests.
- Optional local smoke using checked-in deterministic config if added.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_locked_holdout.py tests/test_workflow.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_locked_holdout.py tests/test_workflow.py -q` passed: 66 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_locked_holdout.py tests/test_workflow.py tests/test_cli_e2e.py -q` passed: 68 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed: 142 tests.
- `.venv/bin/python -m compileall -q src tests` passed.
- `.venv/bin/python -m pip check` passed: no broken requirements.
- `git diff --check` passed.
- `.venv/bin/python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json` passed; locked holdout evidence reported dataset `institutional-golden-holdout-v1`, hash/date/symbol matches, and 944 holdout rows.
