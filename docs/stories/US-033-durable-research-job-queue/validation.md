# Validation

## Proof Strategy

Completion requires durable idempotency, single-claim concurrency, lease expiry
recovery, bounded retry/dead-letter behavior, successful artifact-producing
worker execution, role-scoped API access, and no regression in synchronous batch
execution.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Input validation, state transitions, lease ownership, retry budget. |
| Integration | SQLite idempotency, concurrent claims, expired leases, events. |
| E2E | CLI enqueue, worker run-once, list/show, produced batch artifacts. |
| Platform | FastAPI enqueue/list/show/events with viewer/researcher roles. |
| Performance | Concurrent claim contention remains deterministic for local SQLite. |
| Logs/Audit | Events record transitions and worker ids without secrets. |

## Fixtures

- Temporary SQLite queue.
- Deterministic synthetic research config.
- Fixed worker ids and controlled timestamps.
- Failing batch executor for retry/dead-letter proof.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-033
```

## Acceptance Evidence

- Queue and platform verification passed: `29 passed`.
- Full regression suite passed: `175 passed`.
- Queue suite passed: `13 passed`, covering idempotency, concurrent claims,
  active-lease enforcement, exact-expiry handling, recovery, bounded retry,
  dead letter, worker execution, lease loss, CLI, and token non-persistence.
- CLI smoke enqueued, listed, executed, and showed one real synthetic batch job;
  it completed in one attempt and produced `batch_summary.json`.
- CLI/API serializers and durable event rows do not expose or persist lease
  tokens.
- `compileall`, `pip check`, and `git diff --check` passed.
- `scripts/bin/harness-cli story verify US-033` passed.
