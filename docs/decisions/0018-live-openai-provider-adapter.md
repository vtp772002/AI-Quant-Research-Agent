# Live OpenAI Provider Adapter Boundary

Date: 2026-06-17

## Status

Accepted

## Context

The research loop already supports deterministic, fixture, and guarded command
providers. The next product step is a live LLM provider adapter that can call a
managed model while preserving the existing prompt transcript, strict idea
validation, and human review queue.

Live providers introduce network failure, credentials, vendor response-shape
drift, cost, and prompt governance risk. The adapter must not make live calls by
default, store raw API keys, or let provider output bypass the review gate.

## Decision

Add an opt-in `openai` provider that calls the OpenAI Responses API through a
small stdlib HTTP adapter:

- `deterministic` remains the default provider.
- `openai` requires `--allow-external-llm` or `AIQRA_ALLOW_EXTERNAL_LLM=1`.
- Credentials come from `AIQRA_OPENAI_API_KEY` or `OPENAI_API_KEY`.
- The model must be explicit through `--llm-model` or `AIQRA_OPENAI_MODEL`.
- The API URL can be overridden with `--llm-api-url` or
  `AIQRA_OPENAI_RESPONSES_URL`.
- Prompt, normalized provider response, and transcript artifacts are written as
  before.
- Raw API keys are never written to response, transcript, idea, or review queue
  artifacts.
- Provider output is still converted to `ExperimentIdea`, validated, written to
  a draft review queue, and blocked from execution until approved.

## Alternatives Considered

1. Add a vendor SDK dependency. Deferred to avoid expanding install surface and
   to keep CI deterministic.
2. Pick a default live model in code. Rejected because model availability,
   cost, and policy are operational choices.
3. Reuse the command provider only. Rejected because the repo needs a first
   typed provider adapter to prove credential and transcript boundaries.

## Consequences

Positive:

- Operators can test live idea generation without shelling out to a wrapper
  command.
- The adapter is covered by deterministic fake-transport tests.
- Existing validation and review gates continue to protect generated configs.

Tradeoffs:

- Retry, backoff, rate-limit budgeting, and provider-specific evals are still
  future stories.
- The adapter depends on the Responses API response shape and may need updates
  if the provider contract changes.
- Credentials remain environment-managed rather than stored in a secret manager.

## Follow-Up

- Add prompt regression fixtures from reviewed live transcripts.
- Add retry/rate-limit policy after live usage patterns are known.
- Add provider-specific evals before treating live output as reliable research
  assistance.
