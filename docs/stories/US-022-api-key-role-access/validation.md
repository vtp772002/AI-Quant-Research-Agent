# Validation

## Proof Strategy

The story is done when protected API routes fail closed without configured keys,
reject missing and invalid keys, reject insufficient roles, allow viewer reads,
allow researcher experiment execution, and preserve existing CLI/test behavior.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | API key parser accepts valid roles and rejects invalid roles. |
| Integration | FastAPI route metadata protects every non-health route. |
| E2E | Researcher role can run an experiment through the API route endpoint; viewer can read signals but cannot satisfy researcher dependency. |
| Platform | Full pytest, compileall, diff check, and API auth smoke. |
| Performance | Not applicable. |
| Logs/Audit | Existing request logs remain; authenticated actor logging is deferred. |

## Fixtures

- Temporary synthetic config.
- `AIQRA_API_KEYS=viewer-secret:viewer,research-secret:researcher`.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
PYTHONPATH=src AIQRA_API_KEYS="viewer-secret:viewer,research-secret:researcher" python - <<'PY'
from quant_research_agent.api_auth import clear_auth_cache, require_role
clear_auth_cache()
print(require_role("viewer")("viewer-secret").role)
print(require_role("researcher")("research-secret").role)
PY
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_production_research_platform.py -q`
  passed 7/7.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 36/36.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- API auth smoke with `AIQRA_API_KEYS="viewer-secret:viewer,research-secret:researcher"`
  resolved viewer and researcher roles and returned `HTTPException:403` when a
  viewer key attempted to satisfy the researcher dependency.
