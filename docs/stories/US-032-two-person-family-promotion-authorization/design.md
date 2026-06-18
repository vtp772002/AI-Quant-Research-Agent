# Design

## Domain Model

`promotion_ledger.jsonl` stores immutable recommendation and decision events.
Each event includes:

- schema version and event id;
- event type and timestamp;
- family, hypothesis, candidate, and run ids;
- actor identity and role;
- recommendation id and decision status;
- frozen evidence path and SHA-256;
- previous event hash, event hash, and HMAC-SHA256.

Business rules:

- recommendation role must be `researcher`;
- decision role must be `operator`;
- recommendation requires exactly one selected `FAMILY_PROMOTE` row;
- decision actor must differ from recommendation actor;
- one recommendation is allowed for each family/run pair;
- only pending recommendations can be approved or rejected;
- event hashes bind canonical event content and the previous hash.
- event HMACs require `AIQRA_PROMOTION_LEDGER_HMAC_KEY`;
- mutation transactions are serialized per ledger before validation and append.

## Application Flow

Recommendation:

1. Recompute family comparison from the supplied manifests.
2. Select the requested run and require `FAMILY_PROMOTE`.
3. Freeze the full comparison JSON under an evidence directory.
4. Hash the evidence and append a recommendation event.

Decision:

1. Load and verify the complete ledger.
2. Find the pending recommendation.
3. Enforce operator role and actor separation.
4. Append an approved or rejected decision event.

Verification:

1. Parse every JSONL event.
2. Recompute the event hash chain.
3. Recompute each frozen evidence hash.
4. Re-evaluate roles, uniqueness, and state transitions.
5. Return a machine-readable valid/errors result.

## Interface Contract

CLI:

- `--recommend-family-promotion <manifests>`
- `--decide-family-promotion <recommendation-id>`
- `--promotion-ledger <path>`
- `--promotion-family-id`, `--promotion-run-id`
- `--promotion-decision approved|rejected`
- `--promotion-actor`, `--promotion-role`, `--promotion-note`
- `--verify-promotion-ledger <path>`
- `--list-family-promotions <path>`

API:

- `GET /promotions?family_ledger=<path>` requires viewer.
- `POST /promotions/recommend` requires researcher.
- `POST /promotions/decide` requires operator.
- `GET /promotions/verify?family_ledger=<path>` requires viewer.

Errors use the existing CLI exception behavior and API `400`/`404` boundaries.
Missing promotion signing configuration fails closed.

## Data Model

No mutable database schema is added. The ledger is append-only JSONL and frozen
evidence is stored beside it. Local filesystem durability is the phase
boundary; managed retention remains deferred.

## UI / Platform Impact

CLI and internal API only. No browser, mobile, broker, or cloud-provider
surface changes.

## Observability

API request logs retain the existing sanitized `api_key_id`, role, required
role, and authorization result. Ledger events contain sanitized API actor ids
or explicit CLI actor ids, never raw API keys. API ledger actor ids are
collision-resistant SHA-256 fingerprints separate from masked logging ids.

## Alternatives Considered

1. Mutable approval rows in SQLite.
2. Single-actor promotion.
3. External identity integration before defining the local contract.
