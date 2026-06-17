# Overview

## Current Behavior

The research loop can generate validated idea configs from deterministic,
fixture, or command-backed providers. Provider transcripts are recorded, but the
generated configs can still be passed to alpha-mining execution without a
separate human approval artifact.

## Target Behavior

Generated ideas write a review queue. Each idea starts as `draft`, can be marked
`approved`, `rejected`, `ran`, or `archived`, and only approved configs can run
through the generated-idea execution path unless an operator explicitly uses a
review override.

## Affected Users

- Quant researcher reviewing generated hypotheses.
- Operator running local alpha-mining batches.
- Future developer adding live provider adapters.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Multi-user approval service.
- Auth, role-scoped approval, or immutable audit logs.
- Live LLM provider SDK integration.
