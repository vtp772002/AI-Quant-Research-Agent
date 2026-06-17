# Exec Plan

## Goal

Add a governed LLM provider boundary for research idea generation without
introducing vendor-specific SDKs or unreviewed model output.

## Scope

In scope:

- Prompt/schema payload builder.
- Fixture provider.
- Guarded external command provider.
- Transcript artifacts.
- CLI flags for provider selection.
- Tests for fixture provider and command guard.
- Docs, decision, and Harness records.

Out of scope:

- Direct provider SDKs.
- Credential storage.
- Retry/rate-limit policy.
- Prompt registry service.
- Arbitrary code execution from model output.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Audit/security.
- Existing behavior.

Hard gate:

- External command execution is blocked unless explicitly allowed.

## Work Phases

1. Add provider module.
2. Route generate-ideas and mine-alpha through provider options.
3. Add validation and transcript tests.
4. Update docs, decision, and story packet.
5. Validate and update Harness records.

## Stop Conditions

Pause if a change requires storing credentials, weakening output validation, or
calling a live provider without explicit operator approval.
