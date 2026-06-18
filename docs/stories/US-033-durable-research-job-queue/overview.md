# Overview

## Current Behavior

`run_research_batch()` executes configs synchronously and writes summary and
comparison artifacts. `scripts/run_daily_research.sh` can be called by cron, but
the platform does not preserve queued work or recover safely after worker
failure.

## Target Behavior

The platform provides a durable local research-job queue:

- callers enqueue batch requests with an idempotency key;
- workers transactionally lease one eligible job;
- duplicate submissions return the existing job;
- expired leases are recoverable;
- failures retry within a configured attempt budget and then dead-letter;
- successful workers persist batch artifact paths and run ids;
- lifecycle events are queryable through CLI and the internal API.

## Affected Users

- Research operator scheduling repeatable batches.
- Researcher submitting internal batch jobs.
- Platform operator diagnosing retries and dead-letter jobs.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Redis, Celery, Kafka, or cloud queue deployment.
- A continuously running managed worker service.
- Vendor, broker, or live-trading calls.
- Bypassing idea review or family-promotion controls.
- Distributed lease renewal or heartbeat services.
