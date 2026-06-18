# Automatic Worker Lease Renewal

Date: 2026-06-19

## Status

Accepted

## Context

The local durable queue now supports explicit active-lease renewal and stale
heartbeat diagnostics. The next operational gap is the worker itself:
`run_research_worker_once` can execute a batch longer than its lease window
unless another process renews on its behalf. That creates a legitimate
long-running-job failure mode where another worker can recover the expired
lease while the original executor is still running.

Managed queue adapters remain premature because deployment owner,
credentials, retention, monitoring, and provider-specific failure semantics are
not defined.

## Decision

Add opt-in automatic lease renewal to local research workers:

- `run_research_worker_once` accepts `auto_renew_seconds`;
- `run_research_worker_loop` passes the interval through to each job;
- a background renewal monitor renews the active lease with the existing
  `renew_research_job_lease` command while the executor runs;
- worker result JSON and loop summaries report renewal counts;
- renewal failure returns `lease_lost` and blocks final complete/fail mutation;
- the CLI exposes `--worker-auto-renew-seconds` for run-once and loop workers.

## Alternatives Considered

1. Keep renewal manual only. Rejected because the local worker should be able
   to preserve its own lease during known long-running execution.
2. Implement Redis/Celery/SQS/Kafka now. Deferred because infrastructure
   ownership and failure semantics are not specified.
3. Terminate executor threads when renewal fails. Rejected because arbitrary
   synchronous Python executor cancellation is unsafe without a cooperative
   cancellation contract.

## Consequences

Positive:

- Long-running local workers can preserve ownership without a second renewal
  process.
- Lease renewal still flows through the audited queue primitive.
- Lease loss remains fail-closed at the durable mutation boundary.
- Operators get renewal counts in machine-readable worker summaries.

Tradeoffs:

- Automatic renewal adds a background thread while each job executes.
- Executor work may continue briefly after renewal loss, but final state
  mutation is blocked.
- SQLite remains a local queue, not a distributed worker-liveness service.

## Follow-Up

- Add cooperative executor cancellation only if research batches need early
  stop-on-lease-loss semantics.
- Add managed queue adapters only after deployment ownership, credentials,
  retention, monitoring, and failure semantics are specified.
