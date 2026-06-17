# Overview

## Current Behavior

The research loop can generate deterministic ideas, validate them, write config
variants, critique runs, and mine alpha candidates. It does not yet have a
governed provider boundary for external model payloads.

## Target Behavior

The platform should support deterministic, fixture, and guarded external command
providers for idea generation while preserving validation and transcript
artifacts.

## Affected Users

- Quant researcher reviewing model-generated ideas.
- Agent/operator testing saved model transcripts.
- Future developer adding provider-specific LLM integrations.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Direct vendor SDK integration.
- API key management.
- Prompt registry service.
- Autonomous acceptance of model output.
- Arbitrary code execution from model responses.
