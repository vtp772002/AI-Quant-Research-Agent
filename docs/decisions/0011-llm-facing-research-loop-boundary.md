# LLM-Facing Research Loop Boundary

Date: 2026-06-17

## Status

Accepted

## Context

The platform has strong deterministic research workflow plumbing: factor
signals, backtests, reproducibility manifests, registry memory, batch
orchestration, run comparison, and paper-to-alpha heuristics. The main gap
against LLM-native quant research agents is not another metric table, but a
research loop where an agent proposes hypotheses, validates them, reads prior
run memory, critiques results, and proposes follow-up experiments.

Live LLM providers introduce credentials, prompt/version governance, structured
output validation, reproducibility concerns, and review requirements. The repo
should not make CI or basic research validation depend on external API keys.

## Decision

Add an LLM-facing research loop using strict local contracts:

- `ExperimentIdea` is the schema for generated ideas.
- A validator rejects unknown factors, invalid quantiles, bad holding periods,
  overlapping directions, and unsafe names.
- Research memory reads the SQLite registry and summarizes strong/weak runs.
- The default provider is deterministic, so tests and local workflows remain
  reproducible without API keys.
- Paper-to-alpha v2 returns a validated payload with unsupported concepts and
  bias warnings.
- Alpha mining writes generated config variants and can optionally run them
  through batch orchestration.

A future live LLM provider may be added only behind the same schema and
validator, with explicit credential and prompt-version controls.

## Alternatives Considered

1. Call a live LLM directly from the CLI now. Rejected because credentials,
   prompt versioning, and reproducibility policy are not yet specified.
2. Keep paper-to-alpha as keyword matching only. Rejected because it does not
   create a reusable agentic research contract.
3. Build a full multi-agent debate system now. Deferred until the single-agent
   idea/critic/memory loop is stable and measurable.

## Consequences

Positive:

- The repo gains a real agentic research loop surface without unsafe external
  dependencies.
- The validator creates a stable boundary for future LLM providers.
- Existing registry data becomes useful research memory.

Tradeoffs:

- The default provider is deterministic, not a live LLM.
- The critic is metric-rule based and should be replaced or augmented later by a
  reviewed LLM critic.
- Alpha mining can generate many configs, so run-generated mode should be used
  deliberately.

## Follow-Up

- Add a live LLM provider adapter with prompt/version governance.
- Add multi-agent critic/risk/research-manager roles after the single-loop
  contract is stable.
- Add a richer memory model that indexes factor sets, critique outcomes, and
  rejected hypotheses.
