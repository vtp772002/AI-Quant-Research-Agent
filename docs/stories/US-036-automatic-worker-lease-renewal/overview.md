# Overview

## Current Behavior

US-035 added explicit lease renewal and heartbeat diagnostics. That gives a
trusted worker boundary the primitive it needs, but `run_research_worker_once`
still runs the batch executor synchronously without renewing the lease while
the executor is active. A job that legitimately runs longer than its lease
window can therefore become recoverable by another worker before the first
worker finishes.

## Target Behavior

The local worker can automatically renew its active job lease while a batch
executor is running:

- one-shot and loop workers accept an opt-in renewal interval;
- a background renewal monitor renews the same lease token during executor
  runtime only;
- successful renewals update `lease_expires_at`, `last_heartbeat_at`, and
  durable `lease_renewed` events through the existing queue primitive;
- worker results and loop summaries report renewal counts;
- if renewal fails because the lease is no longer active, the worker returns
  `lease_lost` and does not complete or fail the recovered job;
- public payloads still redact lease tokens.

## Affected Users

- Local research operator running long batch jobs.
- Automation that wants bounded worker loops without manual renewal calls.
- Platform operator diagnosing lease loss during local execution.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Redis, Celery, Kafka, SQS, or cloud queue deployment.
- Distributed liveness guarantees across machines.
- Persisted worker-session ledgers.
- Interrupting or killing in-flight executor code on lease loss.
- Running worker execution inside FastAPI.
- Exposing lease tokens in public job, event, CLI, or API payloads.
