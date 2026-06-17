# Product Docs

This directory contains the living product contracts derived from accepted
project specs. The current product contract is:

- `ai-quant-research-agent.md`: Python CLI workflow for hypothesis, factor
  signal, long-short backtest, metrics, and research report generation.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
