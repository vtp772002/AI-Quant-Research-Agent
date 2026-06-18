# Exec Plan

## Goal

Deliver a durable, idempotent, recoverable local execution boundary around the
existing research batch workflow.

## Scope

In scope:

- SQLite queue and lifecycle event schema.
- Idempotent enqueue and transactional leasing.
- Expired-lease recovery.
- Retry and dead-letter transitions.
- One-shot worker delegating to `run_research_batch`.
- CLI/API enqueue and query surfaces.
- Concurrency, recovery, worker, CLI, and API proof.

Out of scope:

- Managed queues, daemon deployment, cloud credentials, brokers, and live
  providers.
- Lease renewal and distributed heartbeats.
- Changes to research validity, idea review, or family promotion.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Audit/security.
- Durable state migration.

## Work Phases

1. Lock story and decision contracts.
2. Add failing queue-domain tests.
3. Implement enqueue and claim.
4. Add failing recovery and retry tests.
5. Implement worker and interfaces.
6. Run independent review and full verification.
7. Update Harness, commit, and push.

## Stop Conditions

Pause for human confirmation if:

- a real external queue or credentials become mandatory;
- review or promotion gates would need to be weakened;
- worker behavior expands into broker or live-provider execution;
- queue semantics require destructive migration of existing research records.
