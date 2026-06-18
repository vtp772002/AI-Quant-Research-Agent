# Validation

## Proof Strategy

The story is complete when only a verified `FAMILY_PROMOTE` row can be
recommended, only a distinct operator can decide it, untouched ledgers verify,
tampered ledgers/evidence fail, CLI/API paths enforce the same rules, and the
full existing suite remains green.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Recommend eligible evidence; reject non-promote evidence; enforce roles, actor separation, uniqueness, and pending state. |
| Integration | Freeze comparison evidence; append and verify hash chain; reject event and evidence tampering. |
| E2E | CLI recommend, list, decide, and verify workflow. |
| Platform | FastAPI researcher recommendation, operator decision, viewer query and verification. |
| Performance | Not required; ledger sizes are bounded local artifacts. |
| Logs/Audit | API actor ids are sanitized; raw keys never enter ledger events. |

## Fixtures

- Deterministic family manifests containing one pre-registered promotable run.
- Researcher and operator API keys with distinct sanitized actor ids.
- Temporary ledger and evidence directories.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_promotion_authorization.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
python -m compileall src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-032
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_promotion_authorization.py tests/test_production_research_platform.py -q` passed: 24 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed: 161 tests.
- `.venv/bin/python -m compileall -q src tests` passed.
- `.venv/bin/python -m pip check` passed with no broken requirements.
- `git diff --check` passed.
- CLI smoke recomputed `FAMILY_PROMOTE` evidence, wrote one pending
  recommendation, appended a distinct operator approval, and verified a
  two-event HMAC-authenticated ledger with zero errors and no signing-key
  leakage.
- API smoke passed for viewer list/verify, researcher recommendation, operator
  decision, collision-resistant actor fingerprints, and absence of raw API
  keys in the ledger.
- Independent review identified and prompted fixes for concurrent mutation,
  masked actor-id collision, and unauthenticated rehash forgery. Regression
  tests now cover all three findings.
