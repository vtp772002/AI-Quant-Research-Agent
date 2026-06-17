# 0008 Python CLI Quant Research MVP

## Status

Accepted

## Context

The supplied product spec asks for an AI Quant Research Agent that demonstrates
the quantitative research workflow: hypothesis, factor/signal, backtest,
evaluation, and report. The repository previously contained Harness scaffolding
but no application stack or product implementation.

## Decision

Use a Python package with a CLI as the v1 product surface. Use `pandas` and
`numpy` for factor and backtest mechanics, YAML for experiment configuration,
and deterministic synthetic data as the default validation source. Keep Yahoo
Finance support optional for real-market demo runs.

## Consequences

- The MVP can be validated offline and deterministically.
- The code structure matches the quant research domain directly: `data`,
  `factors`, `backtest`, and `agents`.
- The first agent layer is deterministic rather than LLM API-backed, avoiding
  credentials and non-reproducible tests in v1.
- Future work can add paper-to-alpha extraction, LLM hypothesis generation,
  experiment databases, and richer data providers without rewriting the core
  backtest engine.
