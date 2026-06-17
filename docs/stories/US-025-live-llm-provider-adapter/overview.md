# Overview

## Current Behavior

Idea generation supports deterministic output, reviewed fixture responses, and
a guarded external command provider. There is no first-class live provider
adapter, so operators must write a shell wrapper to call a managed LLM.

## Target Behavior

The CLI supports `--llm-provider openai` as an opt-in live provider. The adapter
uses environment-managed credentials, requires explicit external allowance,
writes prompt/response/transcript artifacts, validates the returned
`ExperimentIdea` payloads, and writes generated configs into the existing draft
review queue.

## Affected Users

- Quant researcher testing live idea generation.
- Operator managing LLM credentials and provider model selection.
- Future developer adding provider-specific prompt fixtures and evals.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Default live LLM calls.
- Secret manager integration.
- Provider retry and rate-limit orchestration.
- Prompt eval suite.
- Multi-provider routing.
- Executing generated configs without human approval.
