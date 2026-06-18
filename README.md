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
  report with advisory research-validity evidence.
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
export AIQRA_API_KEYS="local-viewer-change-me:viewer,local-researcher-change-me:researcher"
python -m quant_research_agent.api
curl http://127.0.0.1:8000/health
curl -H "X-API-Key: local-viewer-change-me" "http://127.0.0.1:8000/signals/as-of?config_path=configs/base.yaml&date=2022-12-30"
curl -H "X-API-Key: local-viewer-change-me" "http://127.0.0.1:8000/reviews/ideas?review_queue=results/ideas/review_queue.json"
```

All non-health API routes require `X-API-Key`. Configure keys with
`AIQRA_API_KEYS` as comma-separated `key:role` entries. Roles are `viewer`,
`researcher`, and `operator`; `researcher` and `operator` include viewer
permissions, and experiment execution requires at least `researcher`. Request
logs include sanitized `api_key_id`, `role`, `auth_required`, `auth_result`, and
`required_role`; raw API keys are never logged.

The review queue API exposes read-only summary and audit endpoints for viewer
keys:

- `GET /reviews/ideas?review_queue=<path>`
- `GET /reviews/audit?review_queue=<path>`

Researcher keys can update review state and run approved configs through:

- `POST /reviews/ideas/status`
- `POST /reviews/approved/run`

Family-promotion API operations use the same role boundary:

- `GET /promotions` and `GET /promotions/verify` require viewer.
- `POST /promotions/recommend` requires researcher.
- `POST /promotions/decide` requires operator.

Compare generated runs:

```bash
python -m quant_research_agent.main --compare-runs results/runs --comparison-metric sharpe --limit 10
python -m quant_research_agent.main --compare-runs results/runs --json --output results/run_comparison.json
python -m quant_research_agent.main --compare-family results/runs --family-id synthetic-momentum-low-volatility-v1
python -m quant_research_agent.main --compare-family results/runs --json --output results/family_comparison.json
```

Authorize a family promotion with two distinct actors:

```bash
export AIQRA_PROMOTION_LEDGER_HMAC_KEY="<at-least-16-character-local-secret>"
python -m quant_research_agent.main --recommend-family-promotion results/runs --promotion-family-id synthetic-momentum-low-volatility-v1 --promotion-run-id <run_id> --promotion-actor researcher-alice --promotion-role researcher
python -m quant_research_agent.main --list-family-promotions results/promotions/promotion_ledger.jsonl
python -m quant_research_agent.main --decide-family-promotion <recommendation_id> --promotion-decision approved --promotion-actor operator-bob --promotion-role operator
python -m quant_research_agent.main --verify-promotion-ledger results/promotions/promotion_ledger.jsonl
```

Recommendation recomputes family evidence and accepts only the requested
`FAMILY_PROMOTE` row. The comparison JSON is frozen beside the ledger and bound
to a hash-chained recommendation event. Approval or rejection requires an
operator actor different from the researcher actor. This authorizes progression
to the next research stage; it does not authorize trading. Each event also
carries an HMAC-SHA256 authenticated with
`AIQRA_PROMOTION_LEDGER_HMAC_KEY`; the key is required but never written to the
ledger. Mutations serialize the complete read-check-append transaction.

Run a scheduled-style research batch and publish comparison artifacts:

```bash
python -m quant_research_agent.main --run-batch configs/base.yaml configs/point_in_time_synthetic_demo.yaml --batch-output-dir results/daily
AIQRA_CONFIGS="configs/base.yaml configs/institutional_snapshot_demo.yaml" scripts/run_daily_research.sh
```

Export the local registry for object-store/Postgres handoff:

```bash
python -m quant_research_agent.main --export-registry results/registry_export --registry-path results/experiments.sqlite
python -m quant_research_agent.main --verify-registry-governance results/registry_export
python -m quant_research_agent.main --stage-managed-registry results/managed_registry --registry-governance-dir results/registry_export
python -m quant_research_agent.main --verify-managed-registry results/managed_registry
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
python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider fixture --llm-fixture fixtures/ideas.json --llm-max-requests 1 --llm-max-estimated-cost-usd 0.05 --llm-input-cost-per-1k 0.001 --llm-output-cost-per-1k 0.002 --ideas-output-dir results/ideas
AIQRA_OPENAI_API_KEY="..." AIQRA_OPENAI_MODEL="<model>" python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider openai --allow-external-llm --ideas-output-dir results/live_ideas
python -m quant_research_agent.main --critique-run results/runs/<run_id>/manifest.json
python -m quant_research_agent.main --mine-alpha --config configs/base.yaml --n 5 --mine-output-dir results/alpha_mining
python -m quant_research_agent.main --review-ideas --review-queue results/ideas/review_queue.json
python -m quant_research_agent.main --set-idea-status approved --idea-name <idea_name> --review-queue results/ideas/review_queue.json --review-note "Approved for local validation." --review-actor researcher
python -m quant_research_agent.main --review-audit --review-queue results/ideas/review_queue.json
python -m quant_research_agent.main --run-approved-ideas --review-queue results/ideas/review_queue.json --batch-output-dir results/idea_batches --review-actor batch-runner
```

The LLM-facing provider boundary supports `deterministic`, `fixture`, guarded
external `command`, and opt-in live `openai` providers. Command and OpenAI
providers require `--allow-external-llm` or `AIQRA_ALLOW_EXTERNAL_LLM=1`.
The OpenAI provider reads credentials from `AIQRA_OPENAI_API_KEY` or
`OPENAI_API_KEY`, requires an explicit model via `--llm-model` or
`AIQRA_OPENAI_MODEL`, calls the Responses API, and never writes raw API keys to
artifacts. Prompt, response, and transcript artifacts are written under the
idea output directory for review. Request/cost controls and provider eval
artifacts are written beside the transcript; use `--llm-max-requests`,
`--llm-max-estimated-cost-usd`, `--llm-input-cost-per-1k`,
`--llm-output-cost-per-1k`, and `--llm-expected-output-tokens` to fail closed
before provider transport when an operation exceeds the configured budget.
Token costs are operator-supplied estimates, not embedded vendor billing truth.
Generated ideas also write
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

The institutional snapshot demo also enables a locked holdout manifest:
`data/golden/institutional_locked_holdout_manifest.yaml`.

## Metrics

The research report includes:

- IC mean, standard deviation, t-stat, and hit rate.
- Sharpe ratio.
- Max drawdown.
- Average turnover.
- Total long-short return.
- Chronological train/validation/holdout split, with `test` retained as the
  validation-period compatibility alias.
- Baseline comparison on validation-period metrics.
- Research Validity Gate verdict (`PROMOTE`, `REVIEW`, or `REJECT`) based on
  holdout Sharpe, holdout IC, holdout return, baseline comparison,
  walk-forward stability, data readiness, and Benjamini-Hochberg FDR-adjusted
  holdout IC significance.
- Locked institutional holdout evidence when configured, including manifest
  schema, owner, purpose, source content hash, realized holdout date range,
  symbol set, and row-count validation.
- Cross-run experiment-family comparison verdict (`FAMILY_PROMOTE`,
  `FAMILY_REVIEW`, or `FAMILY_REJECT`) based on pre-registration, provenance
  comparability, run-level validity, and family-level Benjamini-Hochberg
  q-values across related runs.
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
  handoff review, including an immutable governance manifest, artifact hashes,
  retention metadata, family evidence, and a verifiable hash chain.
- Local dry-run managed registry deployment bundles with a Postgres apply plan,
  object-lock inventory, copied governance artifacts, and tamper verification.
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
- Opt-in live OpenAI provider adapter for idea generation with explicit
  external-call allowance, environment-managed credentials, transcript
  metadata, and strict review gating.
- Human review gate for generated research ideas with draft, approved, rejected,
  ran, and archived statuses before generated configs can execute.
- Append-only review audit ledger for generated idea creation, approval,
  rejection, archival, and run marking.
- API key authentication and role-scoped access for the internal FastAPI
  service, keeping `/health` public and protecting research routes.
- Authenticated API request log context with sanitized API key ids, roles, and
  auth results.
- Review queue summary, audit, status-update, and run-approved endpoints behind
  the internal API role boundary.
- Validity verdict and holdout/FDR evidence in reports, CLI JSON,
  reproducibility manifests, registry metrics, and experiment CSV rows.
- Optional locked holdout manifests that fail closed on hash, date range,
  symbol, or row-count mismatch before promotion evidence is accepted.
- Experiment-family metadata in configs, manifests, and registry rows, plus
  CLI family comparison artifacts.
- Two-person family-promotion authorization with researcher recommendation,
  distinct operator decision, frozen comparison evidence, and a verifiable
  append-only hash-chain ledger.

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
  agent contracts, an opt-in live LLM adapter, an internal API, as-of signal
  generation, broker-free execution simulation, human review gating, review
  queue API endpoints for generated ideas, an advisory research-validity gate
  with within-run FDR correction, cross-run experiment-family controls, locked
  institutional holdout manifests, immutable registry governance export packs,
  and deterministic local managed-registry deployment bundles, but no live
  vendor API integration,
  broker-grade locate entitlement feed, paper/live broker execution, order
  management, compliance workflow, live managed Postgres/object-lock registry
  mutation, enterprise identity, tenant-scoped authorization, or managed
  immutable promotion-ledger storage.

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
- API key authentication and role-scoped internal API access.
- Review queue API endpoints for summaries, audit events, status updates, and
  approved-idea batch runs.
- Offline registry export handoff.
- Immutable registry governance export packs with hash-chain verification,
  owner/retention metadata, and family evidence.
- Local dry-run managed registry deployment staging with Postgres apply plans,
  object-lock inventory, and verifier.
- Vendor snapshot boundary, paper-to-alpha templates, and execution simulation.
- Research idea generation, critique, memory, paper-to-alpha v2, and alpha-mining
  orchestration with deterministic fallback, an opt-in live OpenAI provider,
  and human approval before generated idea configs run.
- Advisory research-validity promotion gate with chronological holdout,
  Benjamini-Hochberg FDR correction, named checks, and artifact evidence.
- Cross-run experiment-family controls with pre-registration metadata,
  family-level FDR correction, registry fields, and Markdown/JSON artifacts.
- Locked institutional holdout manifests with fail-closed local validation and
  report/manifest/registry evidence.
- Two-person family-promotion authorization through CLI and role-scoped API
  operations, with frozen evidence and tamper verification.

Deferred until separate stories:

- Credentialed managed Postgres/object-lock provider deployment with applied
  migrations and enforced retention policy.
- Queue-backed scheduler/worker orchestration beyond the provided daily-run script.
- Multi-user SaaS controls beyond local API-key roles and two-person promotion.
- Live commercial data vendor API integration with credentials and rate-limit handling.
- Paper trading, broker integration, hard risk gates, reconciliation, and kill switch controls.
- Managed holdout storage and access-control enforcement beyond local manifests.

## Next Steps

- Add reviewed prompt templates and additional provider-specific adapters after
  live OpenAI transcripts have been reviewed.
- Promote local managed registry deployment bundles into credentialed provider
  adapters after ownership and secrets handling are specified.
- Add direct vendor API and securities-lending integrations after credential,
  entitlement, and provenance contracts are specified.
- Add retention enforcement after managed storage ownership and credentials are
  specified.
- Move family-promotion ledgers into managed immutable storage after ownership,
  secrets, and identity contracts are specified.
- Add paper-trading stories only after risk gates, reconciliation, and kill-switch
  requirements are documented.
