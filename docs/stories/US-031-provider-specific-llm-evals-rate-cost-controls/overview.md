# Overview

## Current Behavior

US-025 added the guarded OpenAI provider adapter and the existing provider
boundary already writes prompt, response, and transcript artifacts. The boundary
still lacks explicit request-budget, estimated-cost, and provider-output eval
artifacts, so a live-provider run can be opt-in and reviewed but not
machine-checked against an operator's run budget before the request is made.

## Target Behavior

The LLM provider boundary records deterministic provider controls and eval
artifacts for non-deterministic providers:

- preflight request-count and estimated-cost controls run before provider
  transport or fixture reads;
- request controls fail closed when `max_requests` or estimated-cost limits are
  exceeded;
- provider eval artifacts check requested idea count, required schema fields,
  allowed factor boundary, unique names, warnings, and confidence range;
- transcript, idea payloads, and CLI JSON include `controls_path` and
  `eval_path`;
- external-provider opt-in and human review queue gates remain unchanged.

## Affected Users

- Research operator controlling live provider spend and request volume.
- Quant researcher reviewing generated research ideas before approval.
- Future developer replacing local proof with real provider-specific eval suites.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`

## Non-Goals

- Calling a real OpenAI endpoint during validation.
- Hard-coding vendor pricing as current billing truth.
- Replacing human review approval gates.
- Adding broker, cloud, or credentialed deployment behavior.
- Persisting provider usage in the SQLite experiment registry.
