# Design

## Domain Model

`research_jobs` stores:

- job and idempotency ids;
- status and serialized config paths;
- output directory, comparison metric, and optional limit;
- attempt count and maximum attempts;
- availability timestamp;
- lease owner, token, and expiry;
- result and error payloads;
- created, updated, started, and completed timestamps.

`research_job_events` is append-only and records enqueue, claim, retry,
completion, dead-letter, and expired-lease recovery transitions using a
monotonic event sequence.

## Application Flow

Enqueue:

1. Validate paths and retry policy.
2. Insert a queued job or return the row already bound to the idempotency key.
3. Append one `enqueued` event only for a new job.

Claim:

1. Start `BEGIN IMMEDIATE`.
2. Find the oldest `queued`, eligible `retryable`, or expired `running` job.
3. Increment attempts and assign worker, lease token, and expiry.
4. Append `claimed` or `lease_recovered` plus `claimed` events.
5. Commit and return the leased job.

Worker:

1. Claim one job.
2. Run `run_research_batch()` with the persisted request.
3. Complete on a successful batch.
4. Mark retryable or dead-letter on exceptions or failed batch status.
5. Return `lease_lost` without mutating the job if another worker recovers the
   lease before the transition is persisted.

## Interface Contract

CLI:

- `--enqueue-research-job <config...>`
- `--job-queue-path <path>`
- `--job-idempotency-key <key>`
- `--job-output-dir <path>`
- `--job-max-attempts <n>`
- `--list-research-jobs`
- `--show-research-job <job-id>`
- `--research-worker-run-once`
- `--worker-id <id>`
- `--worker-lease-seconds <n>`

API:

- `POST /jobs/research` requires researcher.
- `GET /jobs/research` requires viewer.
- `GET /jobs/research/{job_id}` requires viewer.
- `GET /jobs/research/{job_id}/events` requires viewer.

The API enqueues and inspects jobs; it does not run a worker inside an HTTP
request.

## Data Model

The queue uses a separate SQLite file, defaulting to
`results/research_jobs.sqlite`. A unique index on `idempotency_key` protects
duplicate submissions. Claim uses a write transaction so concurrent workers
cannot lease the same active row.

## UI / Platform Impact

CLI and internal API only. Existing synchronous `--run-batch` remains supported.
The daily shell script may enqueue instead of executing inline when explicitly
configured later.

## Observability

Job queries expose status, attempts, lease metadata, result paths, and errors.
Events preserve lifecycle transitions with worker ids but no credentials.
Lease tokens remain internal capabilities on active job rows only. They are
neither copied into event rows nor exposed by public CLI/API payloads.

## Alternatives Considered

1. Reuse review queue JSON.
2. Run workers inside FastAPI background tasks.
3. Select a managed queue provider before proving lifecycle semantics.
