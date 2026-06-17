# Exec Plan

## Goal

Implement the six requested next-step capabilities as safe, deterministic
vertical slices without introducing live provider or broker behavior.

## Scope

In scope:

- Batch orchestration module and CLI path.
- Daily-run script using batch orchestration.
- Registry export module and CLI path.
- `vendor_snapshot` data source boundary.
- Paper-to-alpha template extraction module and CLI path.
- Execution simulation module and CLI path.
- Trace documentation aligned with current Harness CLI behavior.
- Tests and product docs.

Out of scope:

- Live commercial vendor API integration.
- Managed Postgres/object-storage service.
- Auth, authorization, or secret management.
- Broker API, paper trading, order routing, locates, fill reconciliation, or kill
  switch controls.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Data model.
- Audit/security.
- Multi-domain.
- Existing behavior.

Hard gates:

- External provider behavior and broker/execution behavior are explicitly kept
  offline and deterministic in this story.

## Work Phases

1. Inspect existing CLI, workflow, data, registry, and signal boundaries.
2. Add small modules for each extension.
3. Wire CLI flags and script behavior.
4. Add deterministic tests.
5. Update product docs, decision record, and story packet.
6. Validate and update Harness durable records.

## Stop Conditions

Pause if the implementation needs credentials, network provider calls, broker
SDKs, data migration, auth, or weakened validation.
