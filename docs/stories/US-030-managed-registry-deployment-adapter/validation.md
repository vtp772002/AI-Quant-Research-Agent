# Validation

## Proof Strategy

US-030 is complete when a governance pack can be staged into a local managed
registry deployment bundle, the verifier accepts an untouched bundle, tampering
is detected, and the full validation ladder passes.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Identifier/object-prefix validation, artifact hashing, object inventory integrity. |
| Integration | Stage deployment from a governance pack; reject invalid governance pack; verify tamper detection. |
| E2E | CLI export governance pack, stage managed registry bundle, verify managed bundle. |
| Platform | Local filesystem staging; no credential or network dependency. |
| Performance | No benchmark; staging copies a bounded governance pack. |
| Logs/Audit | Harness story, decision, matrix, and trace records. |

## Fixtures

- Temporary SQLite registry rows and governance export packs from
  `export_registry_snapshot`.
- Tampered copied object files and malformed manifests for verifier cases.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_managed_registry.py tests/test_production_extensions.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_managed_registry.py tests/test_production_extensions.py -q` passed: 16 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed: 147 tests.
- `.venv/bin/python -m compileall -q src tests` passed.
- `.venv/bin/python -m pip check` passed: no broken requirements.
- `git diff --check` passed.
- CLI smoke passed: exported registry governance pack, staged local managed registry deployment bundle, and verified deployment with `valid: true`, 4 object-lock artifacts, and no errors.
