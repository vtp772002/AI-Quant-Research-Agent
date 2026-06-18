# Durable Research Job Queue

Date: 2026-06-19

## Status

Accepted

## Context

The platform has a stable synchronous batch function, internal API, local
registry, review gates, and family-promotion controls. Scheduled execution still
depends on a shell script invoking the batch function directly. There is no
durable job state, idempotent submission, lease ownership, crash recovery,
bounded retry, or dead-letter evidence.

Choosing Redis, Celery, or a cloud scheduler now would introduce provider
selection, credentials, deployment ownership, and operational dependencies
before the job contract itself is proven.

## Decision

Add a local SQLite research-job queue:

- enqueue is idempotent by caller-supplied key;
- jobs move through `queued`, `running`, `retryable`, `completed`, and
  `dead_letter`;
- workers claim one job transactionally with a unique lease token and expiry;
- only the current lease holder may complete or fail a running job;
- expired leases become claimable again;
- failures retry up to `max_attempts`, then move to dead letter;
- every lifecycle transition appends a durable job event;
- lease tokens remain only on active job rows and are not copied into events or
  public payloads;
- the worker delegates execution to the existing `run_research_batch`.

SQLite is the authoritative local queue for this phase. The contract is designed
so a later managed queue adapter can preserve the same lifecycle semantics.

## Alternatives Considered

1. Keep cron-only synchronous execution. Rejected because it has no durable
   recovery or duplicate-submission protection.
2. Add Redis/Celery now. Deferred because external deployment and credentials
   are not required to prove the queue semantics.
3. Reuse the experiment registry tables. Rejected because experiment evidence
   and operational job state have different retention and mutation rules.

## Consequences

Positive:

- Scheduled research gains durable state and crash recovery.
- Concurrent workers cannot intentionally claim the same active job.
- Retry and dead-letter outcomes become inspectable.
- Validation remains deterministic and credential-free.

Tradeoffs:

- SQLite is a local single-region queue, not a distributed service.
- Worker liveness still depends on an external process supervisor or cron.
- Long jobs need a future lease-renewal command if they exceed configured
  lease duration.

## Follow-Up

- Add managed queue adapters after deployment ownership is specified.
- Add lease renewal and worker heartbeat only when observed job durations
  require them.
