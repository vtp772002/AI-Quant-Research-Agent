# Overview

## Current Behavior

US-033 added durable job leases and US-034 added a bounded local worker loop.
Workers can recover expired leases, but long-running jobs have no way to renew
an active lease or emit heartbeat evidence before the lease expires. Operators
can inspect jobs and events, but there is no direct stale-worker diagnostic.

## Target Behavior

The platform provides local lease renewal and heartbeat diagnostics for durable
research jobs:

- an active lease holder can renew the job lease without exposing the lease
  token in public payloads;
- claim and renewal update `last_heartbeat_at`;
- renewal appends a durable lifecycle event without copying the lease token;
- stale diagnostics report running jobs with expired leases or old heartbeats;
- CLI and internal API expose renewal and stale diagnostics while preserving
  the existing API rule that workers do not execute inside HTTP requests.

## Affected Users

- Research operator running long local research batches.
- Platform operator diagnosing stale or expired workers.
- Internal automation that renews leases through a trusted worker boundary.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Redis, Celery, Kafka, SQS, or cloud queue deployment.
- Distributed worker coordination or managed queue adapters.
- Persisted worker-session audit tables.
- Running worker execution inside FastAPI.
- Vendor, broker, or live-trading calls.
- Exposing lease tokens in public job, event, CLI, or API payloads.
