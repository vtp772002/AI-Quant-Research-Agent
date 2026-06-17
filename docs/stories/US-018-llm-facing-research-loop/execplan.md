# Exec Plan

## Goal

Add the first LLM-facing research loop while preserving deterministic CI and
safe local execution.

## Scope

In scope:

- Research idea schema and validator.
- Deterministic `LLMResearchAgent` fallback.
- Registry-backed research memory summary.
- Manifest critic and follow-up idea proposal.
- Paper-to-alpha v2 payload.
- Alpha-mining config generation and optional batch execution.
- CLI flags, docs, decision record, and tests.

Out of scope:

- Live LLM provider calls.
- Prompt registry.
- Multi-agent debate.
- Broker or live trading behavior.
- Arbitrary code execution from generated ideas.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Existing behavior.
- Multi-domain.
- Weak proof.

Hard gate:

- External LLM behavior is explicitly not implemented in this story.

## Work Phases

1. Add strict idea schema and validation.
2. Add deterministic idea generator.
3. Add research memory from registry rows.
4. Add run critic and paper-to-alpha v2.
5. Add alpha mining orchestration.
6. Add CLI, tests, docs, decision, and Harness records.

## Stop Conditions

Pause if implementation requires external API keys, arbitrary code execution,
broker behavior, or weakened validation.
