# Validation

## Proof Strategy

The story is done when request log payloads include auth context for public,
successful protected, and failed protected requests, and tests prove raw API
keys are not serialized.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Auth context is recorded for success and failure; public logs default to not required. |
| Integration | Existing API auth dependency and route metadata tests remain green. |
| E2E | Full production platform tests exercise signal read and experiment run with role checks. |
| Platform | Full pytest, compileall, diff check. |
| Performance | Not applicable. |
| Logs/Audit | Log payload includes sanitized `api_key_id`, `role`, `auth_required`, `auth_result`, `required_role`, and excludes raw keys. |

## Fixtures

- `AIQRA_API_KEYS=viewer-secret:viewer,research-secret:researcher`.
- Temporary synthetic config for API route execution.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_research_platform.py -q`
  passed 10/10.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 39/39.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- API auth log smoke resolved `viewer-secret` to role `viewer`, emitted
  sanitized `api_key_id=view...cret`, and verified the raw key was absent from
  the serialized log payload.
