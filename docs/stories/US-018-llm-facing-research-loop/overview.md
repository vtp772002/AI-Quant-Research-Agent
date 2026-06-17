# Overview

## Current Behavior

The platform has deterministic research workflows, registry memory, batch runs,
run comparison, and heuristic paper-to-alpha extraction. It does not yet expose
a validated agent loop for generating ideas, critiquing runs, using prior run
memory, or mining alpha candidates iteratively.

## Target Behavior

The platform should support an LLM-facing research loop:

- Generate validated experiment ideas from a base config and registry memory.
- Write generated ideas as runnable config variants.
- Critique an existing run manifest and propose a follow-up idea.
- Produce paper-to-alpha v2 payloads with validation, unsupported concepts, and
  bias warnings.
- Mine alpha ideas by generating configs and optionally running them through the
  batch orchestrator.

## Affected Users

- Quant researcher exploring factor variants.
- Agent/operator using prior run history as research memory.
- Reviewer checking why a run should be accepted, rejected, or refined.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Live LLM API calls.
- Prompt management service.
- Multi-agent debate.
- Autonomous trading.
- Arbitrary code generation or execution from an LLM.
