# AI Quant Research Agent

## Research Goal

This project explores whether agentic LLM-style workflows can accelerate the
quantitative research loop from hypothesis generation to executable signal,
backtest, metric evaluation, and research reporting.

## Product Surface

The first product surface is a Python CLI:

```bash
python -m quant_research_agent.main --config configs/base.yaml
```

The compatibility entrypoint below is also supported because the original spec
suggested it:

```bash
python -m src.main --config configs/base.yaml
```

The second product surface is an internal FastAPI service:

```bash
python -m quant_research_agent.api
```

It exposes health, metrics, experiment run, experiment lookup, report lookup,
as-of signal, and review queue endpoints for internal research automation. It
is not a public investment-advice API and does not place orders.

The internal API keeps `/health` public for deployment checks. All other routes
require `X-API-Key`; keys are configured with `AIQRA_API_KEYS` as comma-separated
`key:viewer|researcher|operator` entries. Viewer keys can read metrics, runs,
reports, and signals. Researcher and operator keys include viewer permissions;
experiment execution requires at least researcher. Request logs include
sanitized API key id, role, required role, auth-required flag, and auth result;
raw API keys are not logged.

Review queue API reads are available to viewer keys through summary and audit
endpoints. Status updates and approved-idea batch execution require researcher
or operator keys, and write sanitized API actor ids into the review audit
ledger.

## Core Workflow

1. Load OHLCV market data for a configured universe.
2. Diagnose data source quality, panel coverage, and institutional-readiness
   assumptions.
3. Propose or load an alpha hypothesis.
4. Compute a reusable factor library.
5. Convert selected factors into a cross-sectional signal.
6. Diagnose selected factor coverage and pairwise redundancy.
7. Run a long-short backtest with chronological train/test split.
8. Compare the agent signal against configured baseline strategies.
9. Validate signal stability over configured walk-forward windows.
10. Stress-test the agent signal with configured neutralization and liquidity
   constraints.
11. Apply base, spread, and liquidity-sensitive market-impact transaction
   costs plus borrow costs for short exposure.
12. Enforce configured static shortability and date-aware locate availability
   constraints on the short leg.
13. Run configured bootstrap, parameter sensitivity, and cost sensitivity
   robustness diagnostics.
14. Run configured capacity and concentration diagnostics across target
   notionals.
15. Calculate IC, Sharpe ratio, max drawdown, turnover, costs, borrow drag, and
   total return.
16. Write a Markdown research report, append experiment metrics, and emit a
    reproducibility pack manifest for the run.
17. Persist key run metadata and metrics into a queryable local SQLite
    experiment registry.
18. Generate as-of signal snapshots for a requested date using only data
    available on or before that date.
19. Compare reproducibility manifests across prior runs and rank them by a
    selected test-period metric.
20. Run scheduled-style research batches over one or more configs and publish
    batch summaries plus comparison artifacts.
21. Export the local registry as offline object-store/Postgres handoff artifacts.
22. Load vendor snapshot drops through the validated OHLCV snapshot boundary.
23. Extract draft alpha experiment templates from paper or blog text.
24. Simulate as-of execution plans without routing orders or contacting brokers.
25. Generate validated research idea configs from prior run memory, critique
    existing runs, and orchestrate iterative alpha-mining batches.
26. Run idea generation through a governed provider boundary with deterministic,
    fixture, or explicitly allowed command providers and transcript artifacts.
27. Gate generated idea execution behind a human review queue with draft,
    approved, rejected, ran, and archived statuses.
28. Persist an append-only review audit ledger for generated idea creation,
    status changes, and run marking.
29. Protect non-health internal API routes with API keys and role-scoped access.
30. Emit API request logs with sanitized authenticated actor and authorization
    result context.
31. Expose review queue summary, audit, status-update, and run-approved
    operations through the role-scoped internal API.
32. Generate research ideas through an opt-in live OpenAI provider while
    preserving credential guards, transcripts, validation, and review gating.

## Data Contract

Market data is represented as a `pandas.DataFrame` indexed by
`date, symbol` with these columns:

- `open`
- `high`
- `low`
- `close`
- `adj_close`
- `volume`

v1 supports deterministic synthetic data for validation, Yahoo Finance data for
real-market experiments, and CSV snapshot data with manifest validation for
reproducible institutional-style research fixtures.

The Yahoo demo configuration is `configs/yahoo_nasdaq_demo.yaml`. It is intended
for exploratory real-data runs and may fail when the external data provider is
unavailable.

The point-in-time synthetic demo configuration is
`configs/point_in_time_synthetic_demo.yaml`. It uses
`configs/universe_membership_demo.csv` to resolve active universe membership by
date and mask market data outside each symbol's membership interval.

The golden snapshot demo configuration is
`configs/institutional_snapshot_demo.yaml`. It reads
`data/golden/institutional_ohlcv_snapshot.csv`, verifies
`data/golden/institutional_ohlcv_snapshot.yaml`, and reports snapshot
provenance fields including dataset id, vendor, as-of date, SHA-256 validation,
row-count validation, symbol-set validation, date-range validation, and
institutional data flags.

Data integrity diagnostics report requested versus observed symbols, row and
date counts, per-symbol coverage, duplicate index rows, non-positive prices or
volume, stale adjusted closes, extreme adjusted returns, and explicit warnings
when data is not marked point-in-time, survivorship-bias-free, or
institutional-grade for corporate actions.

Universe membership can be static or supplied by a CSV provider with
`symbol,start,end` columns. CSV membership is treated as the point-in-time
adapter surface: it resolves symbols for the experiment date range and removes
rows outside each symbol's membership interval before factors and backtests are
computed.

CSV snapshot market data uses a separate manifest boundary. The manifest is a
small YAML file that records the expected dataset id, vendor, as-of date,
content hash, row count, symbols, date range, and institutional-readiness
flags. When `require_manifest_hash` is enabled, a hash mismatch fails fast
before the research workflow can produce a report. Row-count, symbol-set, and
date-range mismatches are surfaced as provenance warnings and report fields.

## Methodology

Signals are cross-sectional: each factor is ranked across the active universe
on the rebalance date. The portfolio is dollar-neutral, long the top quantile
and short the bottom quantile, rebalanced at a configured interval.

Baseline strategies use the same data, train/test split, rebalance interval,
portfolio construction, and transaction cost assumptions as the agent signal.
This keeps comparison focused on signal quality rather than backtest settings.

When configured, walk-forward validation divides the backtest results into
multiple chronological test windows after an initial expanding training period.
The report summarizes agent-signal stability by window and compares aggregate
walk-forward stability across configured strategies.

Factor diagnostics evaluate the selected agent and baseline factor exposures
before interpreting results. The report shows factor coverage, missing rates,
and high absolute Spearman-correlation pairs so redundant exposures can be
simplified before adding more signal complexity.

Stress tests are optional backtest variants that reuse the same market data,
rebalance cadence, transaction cost assumption, and validation windows as the
agent signal. Sector neutralization subtracts each configured sector's
cross-sectional mean signal on each rebalance date. Liquidity filtering removes
assets below the configured cross-sectional `dollar_volume_20d` rank before
portfolio construction.

Transaction costs include a base turnover cost, spread cost, and
liquidity-sensitive market impact cost. Market impact is estimated from trade
size as a fraction of rolling 20-day average dollar volume using the configured
portfolio notional and impact coefficient. Reports include average base,
spread, impact, total cost, and trade participation diagnostics.

Shorting controls can specify an annualized fallback borrow fee, a static set
of symbols eligible for the short leg, and an optional CSV locate history. If a
static shortable universe is configured, portfolio construction excludes
non-shortable symbols from short candidates. If a locate history is configured,
portfolio construction also requires the date-symbol row to be shortable on
that rebalance date; missing locate rows are treated as not shortable. Borrow
cost is charged on short exposure for the configured holding period using
date-symbol borrow fees from the locate history when available and the fallback
fee otherwise.

Robustness diagnostics are optional post-backtest checks. Bootstrap resampling
estimates confidence intervals and positive-result probabilities for test
Sharpe and test IC. Parameter sensitivity reruns the backtest across configured
holding-period and quantile grids. Cost sensitivity reruns the same signal with
configured transaction-cost and borrow-cost multipliers. These diagnostics do
not prove investment merit, but they make overfit and fragility visible in the
report and CLI JSON.

Capacity diagnostics are optional post-backtest checks. Concentration metrics
measure max single-name weight, effective position count, and gross exposure
from the realized portfolio weights. Capacity curves rerun the same signal
across configured portfolio notionals and report the resulting transaction
costs, market impact, trade participation, test Sharpe, and pass/fail gates for
positive Sharpe and maximum trade participation.

Every CLI run writes a reproducibility pack under `results/runs/<run_id>/`.
The pack includes a frozen config copy and `manifest.json` with run id,
generation timestamp, config SHA-256, git commit/branch/dirty flag, data
fingerprints, locate-history hash when configured, report hash, experiment CSV
hash, and primary metrics. The Markdown report includes a `Run
Reproducibility` section that points to the manifest and frozen config.

Every CLI run also writes a queryable registry row to
`results/experiments.sqlite` by default. The registry stores run id, experiment
name, generated timestamp, config hash, source metadata, code metadata,
artifact paths, and key train/test metrics. It is the Level 1 local system of
record for internal research runs; a Postgres-backed registry is a later
deployment story.

Run comparison reads one manifest file or the `manifest.json` files under a
run-bundle directory such as `results/runs/`. It ranks runs by a selected
test-period metric, emits Markdown or JSON, and warns when compared runs are not
strictly like-for-like because they use different config hashes, git commits,
data sources, snapshot dataset ids, or dirty worktrees.

Batch orchestration runs one or more config files through the same CLI workflow,
records successful run ids, captures per-config failures, and writes comparison
artifacts for the generated run bundle directory. It is suitable for cron,
GitHub Actions, or a future worker, but it is not a queue or distributed
scheduler.

Registry export writes newline-delimited JSON records, an export manifest, and
a reviewable Postgres upsert handoff SQL file from the local SQLite registry.
This is an offline migration and object-store handoff surface, not a managed
database service, migration tool, or retention policy.

Vendor snapshot ingestion treats commercial data as a validated file drop at the
same OHLCV boundary as CSV snapshots. It requires explicit provenance review and
does not fetch live data from vendor APIs or manage credentials.

Paper-to-alpha extraction converts paper/blog text into a draft experiment
template using simple heuristics. The generated hypothesis, factors, and holding
period must be reviewed before they become investment research.

The LLM-facing research loop uses strict `ExperimentIdea` payloads: name,
hypothesis, positive factors, negative factors, holding period, quantile,
rationale, confidence, and warnings. The current implementation includes a
deterministic provider so CI and local validation do not require API keys; a
future live LLM provider must satisfy the same validator and credential boundary.
Research memory reads prior registry rows, idea generation writes config
variants, the critic explains weak or promising runs from manifest metrics, and
alpha mining can optionally run generated configs through the existing batch
orchestrator.

The provider boundary records prompt schema version, prompt payload, provider
response, and transcript metadata. `fixture` providers enable deterministic
review of externally generated JSON. `command` providers are guarded by an
explicit allow flag and environment variable because they can call external
processes. `openai` is an opt-in live provider that requires
`--allow-external-llm` or `AIQRA_ALLOW_EXTERNAL_LLM=1`, reads credentials from
`AIQRA_OPENAI_API_KEY` or `OPENAI_API_KEY`, requires an explicit model, and
writes only normalized response metadata to artifacts. Raw API keys are not
written to prompt, response, transcript, idea, or review queue artifacts. The
platform still rejects invalid provider output before any config is written.

Generated idea configs are not execution-ready by default. Idea generation
writes a `review_queue.json` artifact with one record per config. Records start
as `draft`; an operator can mark them `approved`, `rejected`, or `archived`.
Only approved records are eligible for `--run-approved-ideas` or
other queue-driven execution paths; completed approved runs are marked `ran`.
One-shot `--mine-alpha --run-generated` creates a fresh draft queue and is
blocked by default unless `--review-override` is explicitly supplied. The
override keeps that fact in the review note.

Each review queue also writes `review_audit.jsonl` as an append-only ledger.
The ledger records event id, event type, queue path, idea name, config path,
source, previous status, next status, actor, note, and timestamp. This gives
local research reviews a durable operator trail without introducing auth,
multi-user approvals, or a managed audit database.

The internal API surfaces the same review queue boundary for automation:
viewer keys can read queue summaries and audit events, while researcher keys
can change idea status or run approved configs. API-originated review mutations
record sanitized actor ids such as `api:rese...cret`; raw keys are not written
to audit or request logs.

Execution simulation converts as-of signal target weights into a broker-free
order plan with participation gates. It does not route orders, reserve locates,
send broker instructions, reconcile fills, or implement a kill switch.

As-of signal generation truncates loaded market data to the requested date,
computes configured factors and signal scores, and emits symbol-level signal
score, rank, target weight, reason, data timestamp, model/config version, and
risk status. It does not compute forward returns or claim execution feasibility.

## Limitations

- Synthetic data validates mechanics, not investment merit.
- Yahoo Finance data is useful for demos but not institutional-grade research
  data.
- Data integrity diagnostics identify readiness gaps but do not create
  survivorship-safe data by themselves.
- Walk-forward validation tests temporal stability but does not remove the need
  for better data controls and independent hypothesis review.
- v1 includes liquidity-sensitive transaction costs, borrow fees, shortability
  constraints, robustness diagnostics, and a CSV point-in-time universe adapter,
  plus capacity diagnostics and validated CSV snapshot and locate-history
  adapters, plus reproducibility manifests, run comparison, a local experiment
  registry, scheduled batch orchestration, registry export handoff, vendor
  snapshot ingestion, paper-to-alpha template extraction, LLM-facing research
  idea generation, governed provider transcripts, an opt-in live OpenAI adapter,
  run critique, research memory, iterative alpha mining, an internal API, as-of
  signal snapshots, and broker-free execution simulation, but these remain
  research approximations and do not replace broker execution data, direct
  securities-lending feeds, direct vendor market data APIs, venue routing
  analysis, independent alpha review, multiple-hypothesis controls, immutable
  object storage, multi-user SaaS authorization, provider-specific LLM evals and
  rate-limit orchestration, or a full production execution simulator.
