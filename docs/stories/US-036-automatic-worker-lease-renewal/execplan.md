# Exec Plan

## Goal

Make local research workers preserve their active leases during long-running
batch execution without exposing lease tokens or adding a managed queue
provider.

## Scope

In scope:

- Opt-in automatic renewal interval on one-shot and loop workers.
- Background renewal monitor scoped to a single claimed job.
- Fail-closed `lease_lost` result when renewal fails.
- Worker result and loop summary renewal counts.
- CLI flag for run-once and loop workers.
- Unit, integration, CLI, Harness, and full-regression proof.

Out of scope:

- External queue providers, cloud credentials, or distributed schedulers.
- FastAPI worker execution.
- Persisted worker-session tables.
- Cooperative executor cancellation.

## Risk Classification

Risk flags:

- Concurrency.
- Durable state.
- Audit/security.
- Existing behavior.
- Public CLI contract.

Hard gates:

- Stale worker cannot overwrite a recovered job.
- Lease tokens remain redacted.
- Existing queue and platform tests continue to pass.

## Work Phases

1. Record high-risk intake.
2. Add failing auto-renew and lease-loss worker tests.
3. Implement renewal monitor and worker/loop result metadata.
4. Wire CLI flag.
5. Update story, decision, product docs, architecture, and test matrix.
6. Run focused, full, smoke, and Harness verification.
7. Record trace, commit, and push.

## Stop Conditions

Pause for human confirmation if:

- implementation requires managed queue credentials or external infrastructure;
- lease tokens would need to appear in public payloads, logs, or event rows;
- worker execution must move into FastAPI;
- executor cancellation becomes necessary to preserve durable state.
