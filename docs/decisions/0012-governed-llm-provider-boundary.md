# Governed LLM Provider Boundary

Date: 2026-06-17

## Status

Accepted

## Context

US-018 added the LLM-facing research loop with deterministic idea generation,
strict validation, registry memory, run critique, paper-to-alpha v2, and
alpha-mining config generation. The next step is to make the loop ready for
external LLM integration without binding the repo to a vendor SDK or letting
unreviewed model output become executable research configuration.

Live providers introduce credentials, prompt drift, response-shape drift,
network failure, reproducibility gaps, and human review requirements.

## Decision

Add a governed provider boundary:

- `deterministic` remains the default provider for CI and local reproducibility.
- `fixture` reads a saved JSON response and validates it through the same
  `ExperimentIdea` schema.
- `command` reads prompt JSON from stdin and writes response JSON to stdout, but
  only runs when `--allow-external-llm` or `AIQRA_ALLOW_EXTERNAL_LLM=1` is set.
- Every non-deterministic provider writes prompt, response, and transcript
  artifacts with a prompt/schema version.
- Invalid provider output is rejected before config generation.

## Alternatives Considered

1. Add a direct vendor SDK now. Rejected because credential and prompt
   governance are not yet mature enough.
2. Keep only deterministic generation. Rejected because it prevents realistic
   review of external model payloads.
3. Let provider output write configs directly. Rejected because factor names,
   parameters, and names must pass validation first.

## Consequences

Positive:

- External LLM output can be tested with saved fixtures.
- Future provider-specific adapters can reuse the same prompt/response contract.
- Transcript artifacts support review and reproducibility.

Tradeoffs:

- The command provider is deliberately generic and requires operator setup.
- The platform still does not manage API keys or vendor-specific retry/rate-limit
  behavior.
- Human review remains required before trusting generated research ideas.

## Follow-Up

- Add provider-specific adapters only after credentials, prompt versioning,
  retry policy, and audit requirements are specified.
- Add prompt-template tests and regression fixtures as real model transcripts
  are reviewed.
