# Exec Plan

## Goal

Add the missing local lease-renewal and heartbeat layer around durable research
jobs so long-running worker ownership can remain explicit and diagnosable.

## Scope

In scope:

- SQLite-compatible `last_heartbeat_at` migration.
- Active-lease renewal command that updates heartbeat and lease expiry.
- Stale running-job diagnostics for expired leases and stale heartbeats.
- CLI renewal and stale-diagnostic surfaces.
- Internal API renewal and stale-diagnostic surfaces.
- Unit, integration, platform, Harness, and real CLI proof.

Out of scope:

- External queue providers, cloud credentials, brokers, and distributed
  schedulers.
- Background heartbeat threads around synchronous batch execution.
- Managed worker-session ledger.
- Changes to research validity, idea review, or family promotion.

## Risk Classification

Risk flags:

- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Durable state migration.
- Audit/security.
- Public CLI/API behavior.

## Work Phases

1. Record high-risk intake and story contract.
2. Add failing queue, CLI, and API tests for renewal and diagnostics.
3. Implement heartbeat column migration and queue commands.
4. Wire CLI and API surfaces.
5. Update product docs, architecture, test matrix, and decision record.
6. Run focused, full, smoke, and Harness verification.
7. Record trace, commit, and push.

## Stop Conditions

Pause for human confirmation if:

- renewal requires external coordination or managed queue credentials;
- lease tokens would need to be exposed in public payloads or logs;
- API worker execution becomes necessary;
- schema changes would require destructive migration of existing queue rows.
