# Design

## Domain Model

No new queue table or column is required. Automatic renewal reuses the US-035
`renew_research_job_lease` command so heartbeat semantics and event redaction
stay centralized.

`ResearchWorkerResult` adds:

- `lease_renewals`: count of successful automatic renewals during the job;
- `lease_renewal_error`: redacted error metadata when the renewal monitor loses
  the lease.

`ResearchWorkerLoopSummary` aggregates `lease_renewals` across processed jobs.

## Application Flow

One-shot worker:

1. Claim an eligible job with the existing transactional lease command.
2. If `auto_renew_seconds` is set, start a daemon renewal monitor scoped to the
   claimed job and lease token.
3. Execute the batch through `operations.run_research_batch`.
4. Stop and join the renewal monitor before mutating final job state.
5. If renewal failed, return `lease_lost` with the current stored job and do
   not call complete or fail.
6. Otherwise complete or fail the job through the existing active-lease
   commands.

Worker loop:

1. Pass the same renewal interval into each one-shot job execution.
2. Aggregate renewal counts into the machine-readable loop summary.

## Interface Contract

CLI addition:

- `--worker-auto-renew-seconds <seconds>`

The flag applies to both `--research-worker-run-once` and
`--research-worker-loop`.

Internal Python API additions:

- `run_research_worker_once(..., auto_renew_seconds: float | None = None)`
- `run_research_worker_loop(..., auto_renew_seconds: float | None = None)`

`auto_renew_seconds` must be positive when supplied. Omitted means no background
thread and preserves US-034/US-035 behavior.

## Failure Semantics

Renewal failure is fail-closed. The worker reports `lease_lost` and reads the
current stored job. This prevents a stale executor from overwriting a job
already recovered by another worker.

The executor is not forcefully interrupted on lease loss. Python cannot safely
preempt arbitrary synchronous code here. The guard is applied before final
state mutation, which is the durable consistency boundary.

## Observability

Automatic renewal writes the same `lease_renewed` lifecycle events as explicit
renewal. Worker JSON includes renewal counts and redacted renewal error
metadata. Lease tokens remain private capabilities and are never serialized by
the worker result serializer.

## Alternatives Considered

1. Require external automation to call `--renew-research-job-lease`. Rejected
   for the worker path because local long-running execution should not need a
   second process to preserve its own lease.
2. Add a managed queue adapter first. Deferred because provider ownership,
   credentials, monitoring, retention, and failure semantics remain undefined.
3. Kill executor work immediately when renewal fails. Rejected because safe
   cancellation requires cooperative executor support and a broader execution
   contract.
