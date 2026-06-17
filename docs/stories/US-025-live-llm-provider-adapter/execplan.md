# Exec Plan

## Goal

Add a first-class live OpenAI provider adapter for research idea generation
without weakening prompt transcripts, credential safety, idea validation, or
human review gating.

## Scope

In scope:

- `openai` provider mode.
- Explicit external-call guard.
- Environment-managed credential and model resolution.
- Responses API HTTP adapter using Python stdlib.
- Normalized provider response and transcript metadata.
- Unit/integration tests with fake transport and no network calls.
- Docs, decision record, and Harness evidence.

Out of scope:

- Secret manager integration.
- Retry/backoff/rate-limit scheduler.
- Provider-specific eval suite.
- Multi-provider routing.
- Live network validation in CI.
- Execution of generated ideas without review approval.

## Risk Classification

Risk flags:

- External systems.
- Audit/security.
- Credentials.
- Public CLI contract.
- Existing behavior.

Hard gates:

- External provider behavior.
- Audit/security.

## Work Phases

1. Add story and decision records.
2. Implement guarded `openai` provider adapter.
3. Wire provider options through research agents and CLI.
4. Add fake-transport tests for guards, request shape, transcript safety, and
   validated idea generation.
5. Update docs and validation evidence.
6. Run full validation and update Harness.

## Stop Conditions

Pause for human confirmation if:

- Raw credentials need to be persisted.
- Provider output would bypass `ExperimentIdea` validation.
- Generated configs would need to run without review approval.
- Live network validation becomes mandatory for acceptance.
