# Managed Local Worker Supervision

Date: 2026-06-19

## Status

Accepted

## Context

The durable research-job queue proves idempotent submission, transactional
leases, retry/dead-letter transitions, and one-shot worker execution. Operators
still need a bounded command that can be supervised by cron, launchd, GitHub
Actions, or another local process manager without reimplementing loop behavior
outside the repository.

Jumping directly to Redis, Celery, SQS, or a cloud scheduler would add provider
ownership, credentials, and deployment-specific failure modes before local
worker operations are well specified.

## Decision

Add a managed local worker loop:

- the loop repeatedly delegates to `run_research_worker_once`;
- operators can bound the session by maximum jobs, maximum runtime, first idle
  poll, or process signal;
- SIGINT and SIGTERM request a graceful stop between job attempts;
- each session returns a machine-readable summary with stop reason, processed
  count, idle cycles, and outcome counts;
- the daily research script supports synchronous run, durable enqueue, and
  bounded worker modes.

The worker loop does not add a new durable worker-session table. The existing
job queue and lifecycle events remain the durable operational record.

## Alternatives Considered

1. Require external shell loops only. Rejected because repeated local loops would
   duplicate budget, idle, and summary behavior outside tested code.
2. Add worker heartbeats and lease renewal now. Deferred until long job duration
   evidence requires it.
3. Deploy a managed queue provider now. Deferred until deployment ownership and
   credentials are specified.
4. Run workers inside FastAPI. Rejected because API requests should enqueue and
   inspect jobs, not execute long-running research batches.

## Consequences

Positive:

- Local scheduled execution has a tested worker control plane.
- Operators get bounded runs and machine-readable summaries.
- The existing queue semantics stay local, deterministic, and credential-free.

Tradeoffs:

- Worker session summaries are returned to the caller but not persisted as a
  separate audit table.
- Long jobs still need a future heartbeat or lease-renewal story if they exceed
  configured lease duration.

## Follow-Up

- Add lease renewal and heartbeat if observed research batches exceed normal
  lease windows.
- Add managed queue adapters after deployment ownership and operational
  requirements are defined.
