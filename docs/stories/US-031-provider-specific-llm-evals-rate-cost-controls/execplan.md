# Exec Plan

## Goal

Add provider-specific LLM eval artifacts and fail-closed request/cost controls
for idea generation while preserving external-provider opt-in and human review
gates.

## Scope

In scope:

- Provider control policy and deterministic controls artifact.
- Provider eval artifact for idea-count, schema, factor-boundary, uniqueness,
  warnings, and confidence checks.
- CLI flags for request and estimated-cost controls.
- Tests proving preflight rejection happens before provider transport.
- Docs, decision record, and Harness proof.

Out of scope:

- Live network validation.
- Real vendor billing reconciliation.
- Cloud secrets, broker APIs, or production deployment.
- Weakening review queue approval requirements.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Existing behavior.
- Weak proof.

Hard gates:

- External provider behavior.
- Removing or weakening validation requirements.

## Work Phases

1. Inspect existing LLM provider boundary and CLI surface.
2. Create high-risk story and durable decision record.
3. Implement provider control and eval artifacts.
4. Add targeted provider/control/eval tests.
5. Update docs and test matrix.
6. Run targeted tests, full test suite, compile checks, CLI smoke, Harness
   verify, and trace.

## Stop Conditions

Pause for human confirmation if:

- Real cloud credentials are needed.
- Vendor pricing must be represented as authoritative billing truth.
- Provider behavior requires a live network call to prove the story.
- Existing review gates would need to be weakened.
