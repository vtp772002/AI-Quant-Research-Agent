# Validation

## Proof Strategy

The story is done when worker-loop control flow is proven with deterministic
tests, the CLI can run a real queued synthetic batch through the loop, the daily
script supports enqueue/worker modes, and the existing queue/API/platform tests
still pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Worker loop summary, idle stop, max job budget, runtime budget, deterministic FIFO claim ordering. |
| Integration | Loop delegates to existing one-shot worker and preserves completed queued jobs. |
| E2E | CLI enqueue plus `--research-worker-loop` completes a synthetic batch and emits JSON summary. |
| Platform | `scripts/run_daily_research.sh` enqueue/worker modes operate through the same CLI. |
| Performance | Poll sleep is configurable; bounded loops can avoid unbounded local runs. |
| Logs/Audit | Job lifecycle events remain durable; loop summary exposes session outcome counts without lease tokens. |

## Fixtures

- Temporary SQLite research-job queue.
- Synthetic config generated under pytest temp directories.
- Fixed worker ids and controlled timestamps for deterministic unit tests.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-034
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py -q`
  passed 16/16, including worker loop, max-job/runtime budget, CLI loop, and
  existing queue recovery tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_research_job_queue.py tests/test_production_research_platform.py -q`
  passed 32/32.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed
  178/178.
- `.venv/bin/python -m compileall -q src tests`, `.venv/bin/python -m pip
  check`, and `git diff --check` passed.
- Real CLI smoke enqueued one temporary synthetic job, ran
  `--research-worker-loop --worker-stop-when-idle`, completed the job, returned
  `stop_reason=idle`, `jobs_processed=1`, and did not expose `lease_token`.
- `scripts/run_daily_research.sh` enqueue and worker modes passed with
  `AIQRA_PYTHON=.venv/bin/python`, completed one temporary synthetic job, and
  returned the expected worker summary.
- `scripts/bin/harness-cli story verify US-034` passed 32/32.
- `scripts/bin/harness-cli decision verify 0027` passed 16/16.
