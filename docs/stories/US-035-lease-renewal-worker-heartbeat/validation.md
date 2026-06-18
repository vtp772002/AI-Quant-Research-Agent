# Validation

## Proof Strategy

The story is done when active-lease renewal, stale-token rejection, heartbeat
timestamps, stale diagnostics, CLI/API surfaces, schema migration, and token
redaction are all proven without regressing the durable queue, worker loop, or
internal API tests.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Active worker renews lease, stale holder cannot renew after recovery, heartbeat timestamp updates, stale diagnostic reasons. |
| Integration | SQLite queue migration adds `last_heartbeat_at`; lifecycle events append `lease_renewed` without token persistence. |
| E2E | CLI renews an active lease and returns a redacted JSON job payload. |
| Platform | FastAPI renewal and stale-diagnostic routes are role-scoped and return redacted payloads. |
| Performance | Stale diagnostics use indexed running-job fields and bounded `limit`. |
| Logs/Audit | Renewal events include worker id, expiry, and heartbeat but not lease tokens. |

## Fixtures

- Temporary SQLite queue.
- Fixed timestamps around active and expired leases.
- Directly claimed jobs to obtain internal lease tokens for renewal tests.
- API principals from local API-key auth helpers.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-035
scripts/bin/harness-cli decision verify 0028
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py -q`
  passed 20/20, including active renewal, stale-token rejection, stale
  diagnostics, CLI renewal, worker loop, retry/dead-letter, and token redaction.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q`
  passed 37/37, including API renewal and stale-diagnostic routes.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed
  183/183.
- `.venv/bin/python -m compileall -q src tests`, `.venv/bin/python -m pip
  check`, and `git diff --check` passed.
- Real CLI smoke renewed one active temporary job lease, reported one expired
  stale job, and verified rendered JSON did not include `lease_token` or raw
  token values.
- `scripts/bin/harness-cli story verify US-035` passed 37/37.
- `scripts/bin/harness-cli decision verify 0028` passed 20/20.
