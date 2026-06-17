# AI Quant Research Agent

From hypothesis to alpha signal, backtest, and research report.

This project explores how agentic workflows can assist quantitative researchers
by generating alpha hypotheses, converting them into executable factor signals,
running long-short backtests, and producing research reports with statistical
validation.

## Research Goal

Can an AI agent accelerate the alpha research workflow without hiding the
statistical evidence a quant researcher needs to judge a signal?

## System Design

- `data`: load deterministic synthetic OHLCV data, Yahoo Finance OHLCV data, or
  validated CSV snapshot data with manifest provenance.
- `factors`: compute a reusable factor library with 20+ price, momentum,
  reversal, volatility, volume, and liquidity factors.
- `agents`: create a hypothesis, translate selected factors into a ranked
  signal, compare it with baselines, evaluate the experiment, and write a
  report.
- `backtest`: run a dollar-neutral top/bottom quantile long-short portfolio.
- `api`: expose an internal FastAPI service for health checks, run execution,
  run lookup, report lookup, and as-of signal generation.
- `reports` and `results`: store generated research artifacts.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m quant_research_agent.main --config configs/base.yaml
```

The spec-compatible entrypoint also works:

```bash
python -m src.main --config configs/base.yaml
```

Run the internal research API:

```bash
python -m quant_research_agent.api
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/signals/as-of?config_path=configs/base.yaml&date=2022-12-30"
```

Compare generated runs:

```bash
python -m quant_research_agent.main --compare-runs results/runs --comparison-metric sharpe --limit 10
python -m quant_research_agent.main --compare-runs results/runs --json --output results/run_comparison.json
```

Run a scheduled-style research batch and publish comparison artifacts:

```bash
python -m quant_research_agent.main --run-batch configs/base.yaml configs/point_in_time_synthetic_demo.yaml --batch-output-dir results/daily
AIQRA_CONFIGS="configs/base.yaml configs/institutional_snapshot_demo.yaml" scripts/run_daily_research.sh
```

Export the local registry for object-store/Postgres handoff:

```bash
python -m quant_research_agent.main --export-registry results/registry_export --registry-path results/experiments.sqlite
```

Extract a draft experiment template from paper or blog text:

```bash
python -m quant_research_agent.main --paper-to-alpha papers/example.md --template-output results/paper_alpha_template.yaml
python -m quant_research_agent.main --paper-to-alpha-v2 papers/example.md --template-output results/paper_alpha_payload.json
```

Simulate an as-of execution plan without placing trades:

```bash
python -m quant_research_agent.main --simulate-execution --config configs/base.yaml --as-of-date 2022-12-30 --execution-output results/execution_simulation.json
```

Generate validated research ideas from prior run memory:

```bash
python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --n 10 --ideas-output-dir results/ideas
python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider fixture --llm-fixture fixtures/ideas.json --ideas-output-dir results/ideas
python -m quant_research_agent.main --critique-run results/runs/<run_id>/manifest.json
python -m quant_research_agent.main --mine-alpha --config configs/base.yaml --n 5 --mine-output-dir results/alpha_mining
python -m quant_research_agent.main --review-ideas --review-queue results/ideas/review_queue.json
python -m quant_research_agent.main --set-idea-status approved --idea-name <idea_name> --review-queue results/ideas/review_queue.json --review-note "Approved for local validation." --review-actor researcher
python -m quant_research_agent.main --review-audit --review-queue results/ideas/review_queue.json
python -m quant_research_agent.main --run-approved-ideas --review-queue results/ideas/review_queue.json --batch-output-dir results/idea_batches --review-actor batch-runner
```

The LLM-facing provider boundary supports `deterministic`, `fixture`, and
guarded external `command` providers. Command providers read prompt JSON from
stdin and write strict JSON to stdout, and require `--allow-external-llm` or
`AIQRA_ALLOW_EXTERNAL_LLM=1`. Prompt, response, and transcript artifacts are
written under the idea output directory for review. Generated ideas also write
`review_queue.json`; ideas start as `draft` and must be marked `approved` before
`--run-approved-ideas` can execute them. One-shot
`--mine-alpha --run-generated` is blocked by default because it creates a fresh
draft queue; use `--review-override` only for explicit operator-approved local
experiments. Review creation, status changes, and run marking are also written
to append-only `review_audit.jsonl` events beside the queue.

Run a local production-like container:

```bash
docker compose up --build api
```

## Default Experiment

The default config tests this hypothesis:

```text
Assets with stronger recent momentum and lower realized risk should outperform
over the next 5 trading days.
```

Signal:

```text
rank(momentum_20d) + rank(momentum_60d)
- rank(volatility_20d) - rank(drawdown_20d)
```

Backtest:

```text
Long top 20%, short bottom 20%, rebalance every 5 trading days.
```

Baselines:

```text
momentum_20d_only
low_volatility_only
reversal_5d_only
random_cross_section
```

Real-data demo:

```bash
python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml
```

Point-in-time universe demo:

```bash
python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml
```

Golden snapshot demo:

```bash
python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml
```

## Metrics

The research report includes:

- IC mean, standard deviation, t-stat, and hit rate.
- Sharpe ratio.
- Max drawdown.
- Average turnover.
- Total long-short return.
- Chronological train/test split.
- Baseline comparison on test-period metrics.
- Walk-forward validation across multiple chronological windows.
- Factor coverage and redundancy diagnostics for selected exposures.
- Neutralization and liquidity stress tests for the agent signal.
- Data integrity diagnostics for source quality, panel coverage, and
  institutional-readiness assumptions.
- Base, spread, and liquidity-sensitive market-impact transaction costs.
- Borrow fee, shortability constraints, and date-aware locate availability
  history for short-leg feasibility.
- Point-in-time CSV universe membership adapter for survivorship-safe research
  interfaces.
- Bootstrap confidence intervals, parameter sensitivity grids, and cost
  sensitivity diagnostics for overfit and robustness review.
- Capacity curve, concentration, and trade participation diagnostics for AUM
  feasibility review.
- CSV snapshot manifest validation for dataset provenance, SHA-256 content
  checks, row counts, symbol sets, date ranges, and institutional data flags.
- Per-run reproducibility packs with run id, config hash, code version, data
  fingerprints, artifact hashes, frozen config, and manifest JSON.
- Queryable SQLite experiment registry at `results/experiments.sqlite` by
  default, populated from reproducibility manifests.
- As-of signal generation for daily research automation without using future
  returns.
- Run comparison tooling over reproducibility manifests, with provenance
  warnings when compared runs use different configs, commits, data sources, or
  dirty worktrees.
- Scheduled-style batch orchestration that runs one or more configs and writes
  batch summaries plus comparison artifacts.
- Offline registry export artifacts for object-store and Postgres migration
  handoff review.
- Vendor snapshot ingestion through the same validated OHLCV snapshot boundary.
- Heuristic paper-to-alpha extraction into draft experiment templates.
- Broker-free execution simulation that applies participation gates without
  routing, reserving locates, or placing orders.
- LLM-facing research agent contracts with deterministic fallback for idea
  generation, strict factor validation, run critique, memory-aware config
  generation, paper-to-alpha v2 payloads, and iterative alpha-mining orchestration.
- Governed LLM provider boundary with prompt/schema versioning, fixture provider
  tests, guarded external command execution, transcript artifacts, and validator
  enforcement before generated ideas become configs.
- Human review gate for generated research ideas with draft, approved, rejected,
  ran, and archived statuses before generated configs can execute.
- Append-only review audit ledger for generated idea creation, approval,
  rejection, archival, and run marking.

## Validation

```bash
python -m pytest
python -m quant_research_agent.main --config configs/base.yaml --json
python -m quant_research_agent.api
```

## Limitations

- Synthetic data validates mechanics but is not investment evidence.
- Yahoo Finance is a convenient demo source, not an institutional data source;
  reports flag this explicitly in the data integrity section.
- v1 has diagnostic neutralization, liquidity stress tests, robustness checks,
  capacity diagnostics, a liquidity-sensitive transaction cost model, borrow
  constraints, a CSV locate-history adapter, run comparison, a local experiment
  registry, scheduled batch orchestration, registry export handoff, vendor
  snapshot ingestion, paper-to-alpha template extraction, LLM-facing research
  agent contracts, an internal API, as-of signal generation, and broker-free
  execution simulation, plus human review gating for generated ideas, but no
  live vendor API integration, broker-grade locate entitlement feed, auth,
  paper/live broker execution, order management, or compliance workflow.

## Production Readiness Path

This repo is now aimed at Level 1 first: an internal production research
platform. It is not a live trading system.

Implemented Level 1 foundations:

- Dockerfile and `docker-compose.yml` for the internal API.
- `.env.example` with non-secret local defaults.
- GitHub Actions test workflow.
- Queryable experiment registry.
- As-of signal API.
- Batch run orchestration and run comparison artifacts.
- Offline registry export handoff.
- Vendor snapshot boundary, paper-to-alpha templates, and execution simulation.
- Research idea generation, critique, memory, paper-to-alpha v2, and alpha-mining
  orchestration with deterministic fallback and human approval before generated
  idea configs run.

Deferred until separate stories:

- Managed Postgres/object-storage registry with migrations and retention policy.
- Queue-backed scheduler/worker orchestration beyond the provided daily-run script.
- Auth, authorization, and multi-user SaaS controls.
- Live commercial data vendor API integration with credentials and rate-limit handling.
- Paper trading, broker integration, hard risk gates, reconciliation, and kill switch controls.

## Next Steps

- Add auth and role-scoped access for the internal API.
- Add a live LLM provider adapter after prompt/versioning, credentials, and
  review requirements are specified.
- Add reviewed prompt templates and provider-specific adapters after the
  external command boundary has stable transcripts and review queue evidence.
- Promote registry export handoff into managed Postgres/object-storage deployment.
- Add direct vendor API and securities-lending integrations after credential,
  entitlement, and provenance contracts are specified.
- Add paper-trading stories only after risk gates, reconciliation, and kill-switch
  requirements are documented.
