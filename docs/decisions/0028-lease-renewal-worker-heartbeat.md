# Lease Renewal And Worker Heartbeat

Date: 2026-06-19

## Status

Accepted

## Context

The durable research-job queue has transactional leases, retries, dead letters,
and local worker-loop supervision. Long-running jobs still need a way for the
active lease holder to renew ownership before expiry. Operators also need a
read-only way to detect running jobs whose leases have expired or whose
heartbeats are stale.

Managed queues remain premature because deployment ownership, credentials,
retention, monitoring, and failure semantics are not yet specified.

## Decision

Add local SQLite lease renewal and worker heartbeat semantics:

- add `last_heartbeat_at` to `research_jobs` with an additive migration;
- set heartbeat timestamp on claim;
- allow only the current active lease token to renew a running job;
- renewal extends `lease_expires_at`, updates `last_heartbeat_at`, and appends a
  `lease_renewed` event;
- stale diagnostics identify running jobs with expired leases, missing
  heartbeat data, or heartbeats older than a configured threshold;
- CLI and internal API expose renewal and stale diagnostics without exposing
  lease tokens in public payloads or event rows.

## Alternatives Considered

1. Deploy Redis/Celery/SQS/Kafka first. Rejected because this phase needs local,
   deterministic ownership semantics before provider selection.
2. Add a persisted worker-session table. Deferred because job events and
   heartbeat fields are enough for current local diagnosis.
3. Make FastAPI run workers and renew leases internally. Rejected because HTTP
   requests should enqueue, inspect, or renew trusted internal state, not own
   long-running research execution.
4. Auto-renew every batch with a background thread. Deferred until long-running
   batch duration patterns justify the added concurrency surface.

## Consequences

Positive:

- Long-running local workers have an explicit renewal primitive.
- Operators can diagnose stale running jobs without reading raw SQLite rows.
- Lease tokens remain private capabilities.
- Existing queue files migrate without destructive changes.

Tradeoffs:

- Renewal is explicit; automatic background renewal remains future work.
- SQLite remains a local queue, not a distributed liveness service.

## Follow-Up

- Add automatic renewal around batch execution if observed jobs routinely exceed
  normal lease windows.
- Add managed queue adapters after deployment ownership and monitoring
  requirements are specified.
