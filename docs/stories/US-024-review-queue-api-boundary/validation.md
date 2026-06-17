# Validation

## Proof Strategy

The story is done when review queue summary and audit endpoints are protected
for viewers, mutation and run-approved endpoints are protected for researchers,
and API-originated mutations append sanitized API actors to the review audit
ledger.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Review queue status update and run marking retain existing audit events. |
| Integration | FastAPI route metadata proves all review endpoints have role dependencies. |
| E2E | API endpoints generate a queue, approve an idea, run approved configs, and observe created/status_changed/ran audit chain. |
| Platform | Full pytest, compileall, diff check. |
| Logs/Audit | Review audit actor is sanitized `api:<api_key_id>` and excludes raw keys. |

## Fixtures

- `AIQRA_API_KEYS=viewer-secret:viewer,research-secret:researcher`.
- Temporary synthetic config and deterministic generated idea queue.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_research_platform.py -q`
  passed 12/12.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 41/41.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- API review queue tests generated a deterministic queue, read summary and
  audit through viewer/researcher principals, approved the idea, ran approved
  configs, and verified the `created`, `status_changed`, `ran` audit chain
  used sanitized actor `api:rese...cret`.
