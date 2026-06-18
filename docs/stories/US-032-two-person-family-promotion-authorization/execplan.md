# Exec Plan

## Goal

Add a deterministic, tamper-evident two-person authorization boundary around
family promotion without weakening the existing research-validity gates.

## Scope

In scope:

- Family evidence recomputation and freezing.
- Hash-chained recommendation and decision ledger.
- HMAC event authentication and serialized ledger mutations.
- Distinct researcher/operator enforcement.
- CLI and role-scoped internal API operations.
- Unit, integration, E2E, and platform smoke proof.

Out of scope:

- External identity, tenants, cloud credentials, brokers, and live trading.
- Managed database or object-lock mutation.
- Scheduler/worker orchestration.

## Risk Classification

Risk flags:

- Authorization.
- Audit/security.
- Data model.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Authorization.
- Audit/security.

## Work Phases

1. Lock story and decision contracts.
2. Add failing domain tests.
3. Implement the ledger and verifier.
4. Add failing CLI/API tests.
5. Implement interfaces and role checks.
6. Run full validation and update Harness evidence.

## Stop Conditions

Pause for human confirmation if:

- external identity or cloud credentials become mandatory;
- implementation requires weakening `FAMILY_PROMOTE`;
- approval semantics extend into trading or compliance authorization;
- existing validation requirements would need to be removed.
