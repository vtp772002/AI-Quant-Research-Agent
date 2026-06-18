# Two-Person Family Promotion Authorization

Date: 2026-06-18

## Status

Accepted

## Context

US-027 can produce a deterministic `FAMILY_PROMOTE` verdict, while US-028
through US-030 preserve and stage the supporting evidence. The verdict remains
advisory and can be acted on by one local operator without a separate
recommendation, approval, or tamper-evident decision record.

Promotion is a higher-risk action than computing research evidence. It needs a
local authorization boundary that can be proven without adding an external
identity provider or managed database.

## Decision

Add an artifact-first family-promotion ledger:

- a researcher may recommend exactly one `FAMILY_PROMOTE` run;
- the recommendation recomputes family evidence from source manifests and
  freezes the comparison as a hashed JSON artifact;
- only an operator with a different actor identity may approve or reject it;
- recommendation and decision events form an append-only SHA-256 hash chain;
- every event carries an HMAC-SHA256 authenticated by
  `AIQRA_PROMOTION_LEDGER_HMAC_KEY`;
- mutations lock the complete read-check-append transaction per ledger;
- verification fails on event mutation, invalid state transitions, duplicate
  recommendations, role violations, same-actor approval, or evidence drift;
- CLI and internal API operations use the same domain boundary.

The first implementation remains local and deterministic. API-key roles supply
a collision-resistant actor fingerprint; CLI users must explicitly supply actor
and role fields. The signing key is required but never persisted.

## Alternatives Considered

1. Treat `FAMILY_PROMOTE` as final approval. Rejected because statistical
   evidence and operational authorization are different controls.
2. Require an external identity provider first. Deferred because the local
   API-key boundary can prove the workflow contract without external secrets.
3. Store mutable approval state in SQLite. Rejected for this phase because an
   append-only artifact with a hash chain is easier to inspect and verify
   alongside existing governance packs.

## Consequences

Positive:

- Promotion requires two distinct role-scoped actors.
- Decisions are bound to exact family-comparison evidence.
- Tampering without the protected signing key and invalid transitions are
  machine-detectable.
- The contract remains testable without cloud credentials.

Tradeoffs:

- API-key identities are local service identities, not enterprise users.
- Local files do not provide managed retention or object-lock enforcement.
- Signing-key distribution and rotation remain operator responsibilities.
- The ledger authorizes research promotion only; it does not authorize trading.

## Follow-Up

- Move the verified ledger to managed immutable storage after provider
  ownership and credentials are specified.
- Add external identity and tenant scope only when the product becomes
  multi-user.
