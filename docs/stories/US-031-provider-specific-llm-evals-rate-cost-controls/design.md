# Design

## Domain Model

`ProviderControlPolicy` is the operator-supplied provider budget:

- `max_requests`;
- `max_estimated_cost_usd`;
- `input_cost_per_1k_tokens_usd`;
- `output_cost_per_1k_tokens_usd`;
- `expected_output_tokens`.

`ProviderArtifacts` now includes:

- `prompt_path`;
- `response_path`;
- `transcript_path`;
- `controls_path`;
- `eval_path`.

The controls artifact uses `llm_provider_controls_v1`. The eval artifact uses
`llm_provider_eval_v1`.

## Application Flow

1. `main` parses LLM control flags and creates a `ProviderControlPolicy`.
2. `research_agents` passes the policy to `llm_provider`.
3. `llm_provider` writes the prompt artifact and preflight controls.
4. If request or cost controls fail, the provider call is rejected before any
   external transport or fixture read.
5. If controls pass, the provider response is obtained and written.
6. Completed controls are rewritten with response usage when available.
7. Provider eval checks the returned ideas before downstream config generation.
8. `research_agents` still validates `ExperimentIdea` objects and writes the
   draft review queue.

## Interface Contract

```bash
python -m quant_research_agent.main \
  --generate-ideas \
  --config configs/base.yaml \
  --llm-provider fixture \
  --llm-fixture fixtures/ideas.json \
  --llm-max-requests 1 \
  --llm-max-estimated-cost-usd 0.05 \
  --llm-input-cost-per-1k 0.001 \
  --llm-output-cost-per-1k 0.002 \
  --ideas-output-dir results/ideas
```

The command exits non-zero if controls reject the request or provider eval
fails. Successful JSON output includes `controls_path` and `eval_path` beside
the existing provider artifacts.

## Data Model

No database schema migration. Provider controls and evals are JSON artifacts
under the existing `llm_transcripts/` directory.

## UI / Platform Impact

CLI-only. No FastAPI or frontend surface changes.

## Observability

Controls record planned request count, configured limits, token estimates,
operator-supplied rates, estimated cost, provider usage when available, and
rejection reasons. Eval records each check and pass/fail status.

## Alternatives Considered

1. Hard-code provider pricing. Rejected because pricing changes and this phase
   should not claim live vendor billing truth.
2. Only evaluate after downstream `ExperimentIdea` validation. Rejected because
   provider-specific eval artifacts need to exist at the provider boundary.
3. Sleep-based rate limiting. Rejected for this CLI phase because there is one
   provider request per operation; a fail-closed request budget is the smaller
   verifiable control.
