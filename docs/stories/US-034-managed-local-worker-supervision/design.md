# Design

## Domain Model

`ResearchWorkerLoopSummary` records one local worker session:

- worker id;
- stop reason;
- number of processed non-idle jobs;
- idle cycle count;
- outcome counts by worker result;
- session start and finish timestamps.

The existing `research_jobs` and `research_job_events` tables remain the source
of durable job state. This story does not add a new queue table or persist
worker sessions in SQLite.

## Application Flow

The loop repeatedly delegates to `run_research_worker_once()`:

1. Check stop request.
2. Check job-count and runtime budgets.
3. Claim and run at most one job through the existing worker.
4. Count non-idle outcomes.
5. On idle, increment idle cycles, optionally stop, otherwise sleep for the poll
   interval.
6. Return a summary when a stop condition is reached.

SIGINT and SIGTERM set a stop event. The loop observes that event between job
attempts, so it does not interrupt an in-flight research batch or mutate queue
state outside the existing lease transition functions.

## Interface Contract

CLI additions:

- `--research-worker-loop`
- `--worker-poll-seconds <n>`
- `--worker-max-jobs <n>`
- `--worker-max-runtime-seconds <n>`
- `--worker-stop-when-idle`

The CLI prints a JSON summary:

```json
{
  "worker_id": "daily-worker",
  "stop_reason": "idle",
  "jobs_processed": 1,
  "idle_cycles": 1,
  "outcome_counts": {"completed": 1},
  "started_at": "...",
  "finished_at": "..."
}
```

Exit code is non-zero when terminal worker outcomes include `dead_letter` or
`lease_lost`; otherwise it is zero.

## Data Model

No schema migration. Claim ordering is made deterministic for equal timestamps
by using SQLite insertion order after `created_at`, preserving local FIFO
semantics without changing stored columns.

## UI / Platform Impact

CLI and shell script only. `scripts/run_daily_research.sh` accepts
`AIQRA_DAILY_MODE`:

- `run-batch` keeps the existing synchronous behavior;
- `enqueue` submits a durable job;
- `worker` runs a bounded local worker loop with `--worker-stop-when-idle`.

## Observability

Worker loop summaries provide session-level operational evidence. Durable job
events continue to record lifecycle transitions and worker ids without lease
tokens or credentials.

## Alternatives Considered

1. Use an external supervisor only. Rejected because operators still need a
   stable bounded worker command and machine-readable session summary.
2. Add a persisted heartbeat table now. Deferred until observed job durations
   require lease renewal or heartbeat diagnostics.
3. Run workers inside FastAPI. Rejected because HTTP requests should enqueue and
   inspect jobs, not own long-running batch execution.
