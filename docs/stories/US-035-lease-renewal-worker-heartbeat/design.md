# Design

## Domain Model

`research_jobs` gains `last_heartbeat_at`.

`ResearchJob` includes the heartbeat timestamp for internal code and public
serializers. The lease token remains internal and is still omitted from public
job/event payloads.

`ResearchJobStaleDiagnostic` reports:

- redacted job payload;
- stale reason;
- observed timestamp;
- heartbeat threshold;
- heartbeat age;
- last heartbeat timestamp;
- lease expiry timestamp.

Stale reasons:

- `lease_expired` when the running job lease is already expired;
- `missing_heartbeat` for legacy running jobs without heartbeat data;
- `heartbeat_stale` when heartbeat age exceeds the configured threshold while
  the lease is not yet expired.

## Application Flow

Claim:

1. Existing claim semantics assign worker, lease token, and lease expiry.
2. Claim now also sets `last_heartbeat_at` to the claim timestamp.

Renew:

1. Validate positive lease duration.
2. Start `BEGIN IMMEDIATE`.
3. Load the job by id.
4. Require status `running`, exact active lease token, and unexpired lease.
5. Update `lease_expires_at`, `last_heartbeat_at`, and `updated_at`.
6. Append `lease_renewed` event with worker id, new expiry, and heartbeat
   timestamp.
7. Return the redacted public job payload through CLI/API serializers.

Diagnostics:

1. Query running jobs whose lease is expired, heartbeat is missing, or heartbeat
   is older than the threshold.
2. Return redacted diagnostics ordered by queue insertion order.

## Interface Contract

CLI additions:

- `--renew-research-job-lease <job-id>`
- `--job-lease-token <token>`
- `--list-stale-research-jobs`
- `--stale-after-seconds <n>`

API additions:

- `POST /jobs/research/{job_id}/lease/renew` requires researcher.
- `GET /jobs/research/stale` requires viewer.

The API still does not execute worker code inside HTTP requests.

## Data Model

SQLite migration is additive:

```sql
ALTER TABLE research_jobs ADD COLUMN last_heartbeat_at TEXT;
```

`initialize_research_job_queue()` applies the missing column check so old local
queue files migrate when touched.

## UI / Platform Impact

CLI and internal API only. No browser or mobile surface.

## Observability

`lease_renewed` lifecycle events provide an audit trail for renewal without
recording lease tokens. Stale diagnostics are read-only and expose worker id,
heartbeat, and lease expiry through existing redacted job payloads.

## Alternatives Considered

1. Add a managed queue adapter first. Rejected because this phase is about local
   semantics and credential-free proof.
2. Persist a worker-session table. Deferred until session retention and owner
   requirements are defined.
3. Add background heartbeat threads around every batch run. Deferred because the
   current safe primitive is explicit active-lease renewal; automatic renewal can
   be layered on top when long-running batch behavior is better characterized.
