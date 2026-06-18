# Overview

## Current Behavior

US-033 added a durable research-job queue and a one-shot worker. Operators can
enqueue jobs, claim one job, inspect state, and recover expired leases. Running
the worker repeatedly still depends on an external loop, shell wrapper, or
process supervisor with no machine-readable session summary.

## Target Behavior

The platform provides a managed local worker loop for durable research jobs:

- operators can run a supervised worker loop from the CLI;
- the loop polls the durable queue and processes jobs sequentially;
- the loop can stop after a maximum job count, maximum runtime, first idle poll,
  or SIGINT/SIGTERM;
- each session returns a JSON summary with stop reason, processed count, idle
  cycles, and outcome counts;
- the daily research script can either run synchronously, enqueue a job, or run
  a bounded worker loop.

## Affected Users

- Research operator running local scheduled research.
- Platform operator diagnosing durable queue processing.
- Researcher relying on repeatable batch execution artifacts.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Redis, Celery, Kafka, SQS, or cloud scheduler deployment.
- Distributed lease renewal or heartbeat services.
- Running workers inside the FastAPI process.
- Vendor, broker, or live-trading calls.
- Weakening idea review, validity, or family-promotion controls.
