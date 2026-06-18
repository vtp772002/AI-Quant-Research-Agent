# Validation

## Proof Strategy

The story is done when automatic renewal is proven during a long-running local
executor, renewal loss is proven fail-closed, CLI accepts the renewal interval,
and existing durable queue/API behavior remains compatible.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Worker starts automatic renewal, records renewal count, rejects non-positive interval. |
| Integration | Long-running executor observes `lease_renewed`; recovered lease is not overwritten. |
| E2E | CLI run-once accepts `--worker-auto-renew-seconds` and returns worker JSON with renewal fields. |
| Platform | Existing internal API renewal/stale diagnostics continue to pass unchanged. |
| Logs/Audit | Renewal events remain redacted and worker result never serializes lease tokens. |

## Fixtures

- Temporary SQLite queue.
- Fake long-running batch executor.
- Fake renewal path that recovers the lease with another worker before the
  stale worker finishes.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-036
scripts/bin/harness-cli decision verify 0029
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py -q`
  passed 23/23, including automatic renewal, fail-closed lease loss, invalid
  renewal interval rejection, CLI worker schema, retry/dead-letter, worker
  loop, and token redaction.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q`
  passed 40/40, including unchanged internal API renewal and stale-diagnostic
  routes.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed
  186/186.
- `.venv/bin/python -m compileall -q src tests`, `.venv/bin/python -m pip
  check`, and `git diff --check` passed.
- Real CLI smoke enqueued one temporary job and completed it with
  `--worker-auto-renew-seconds 0.001`, returning worker JSON with
  `lease_renewals` and no `lease_token`.
- `scripts/bin/harness-cli story verify US-036` passed 40/40.
- `scripts/bin/harness-cli decision verify 0029` passed 23/23.
