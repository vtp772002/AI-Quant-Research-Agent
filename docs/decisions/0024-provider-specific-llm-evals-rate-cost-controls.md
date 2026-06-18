# Provider-Specific LLM Evals And Cost Controls

Date: 2026-06-18

## Status

Accepted

## Context

The project already has a governed provider boundary and opt-in OpenAI adapter.
That boundary prevents accidental external calls and writes prompt/response
transcripts, but it does not yet record explicit request-budget, estimated-cost,
or provider-output eval evidence.

This phase must strengthen the live-provider path without requiring real
credentials, live network calls, or authoritative vendor-pricing assumptions.

## Decision

Add provider controls and eval artifacts at the `llm_provider` boundary.
Provider controls run before provider transport and reject requests when the
operator-supplied request or estimated-cost budgets are exceeded. Provider evals
run after a response and check the returned ideas before downstream config
generation.

CLI flags expose the policy:

- `--llm-max-requests`
- `--llm-max-estimated-cost-usd`
- `--llm-input-cost-per-1k`
- `--llm-output-cost-per-1k`
- `--llm-expected-output-tokens`

Rates are operator-supplied estimates, not embedded vendor billing truth.

## Alternatives Considered

1. Hard-code OpenAI pricing. Rejected because pricing is unstable and would make
   local tests imply live billing truth.
2. Evaluate only after `ExperimentIdea` validation. Rejected because the
   provider boundary needs machine-readable provider-specific evidence.
3. Add a sleep-based limiter. Rejected because this CLI path performs one
   provider request per operation; request-budget rejection is the verifiable
   first control.

## Consequences

Positive:

- Provider runs gain deterministic request/cost evidence.
- Over-budget runs fail before external transport.
- Reviewers can inspect controls/eval paths from CLI output and transcripts.
- Existing external opt-in and human review gates remain intact.

Tradeoffs:

- Cost is estimated from configured rates, not reconciled to provider invoices.
- Rate limiting is per CLI operation, not a distributed quota service.
- Real provider-specific eval suites remain future work.

## Follow-Up

- Add persistent quota accounting if multiple provider requests are introduced.
- Add real provider usage reconciliation only after secrets handling and billing
  ownership are specified.
