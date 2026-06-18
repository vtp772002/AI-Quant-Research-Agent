# Exec Plan

## Goal

Turn the durable local research-job queue into an operationally usable local
worker surface without adding cloud credentials or distributed infrastructure.

## Scope

In scope:

- Worker loop domain function and summary DTO.
- CLI flags for worker loop, polling, job budget, runtime budget, and idle stop.
- Graceful SIGINT/SIGTERM stop request handling.
- Daily script mode selection for synchronous run, enqueue, and bounded worker.
- Unit, integration, CLI, script, and Harness proof.

Out of scope:

- External queue providers and credentials.
- Lease renewal, heartbeat tables, or distributed liveness checks.
- API endpoint that executes workers.
- Changing queue retry/dead-letter semantics beyond deterministic FIFO claim
  ordering for equal timestamps.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Durable operational state.
- Public CLI behavior.

## Work Phases

1. Record high-risk intake and story contract.
2. Add failing worker-loop and CLI tests.
3. Implement worker-loop summary and CLI controls.
4. Add operational script mode support.
5. Update product docs, architecture, test matrix, and decision record.
6. Run focused, story, and full verification.
7. Record Harness proof, commit, and push.

## Stop Conditions

Pause for human confirmation if:

- cloud queue, credentials, or external scheduler ownership becomes mandatory;
- worker execution would move into the FastAPI request process;
- review, validity, or promotion gates would need to be bypassed;
- queue schema migration would risk existing durable job records.
