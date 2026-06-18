# AI Quant Research Report

## Experiment

- Name: `yahoo_nasdaq_momentum_low_volatility`
- Universe: 20 assets from `yahoo`
- Date range: 2020-01-01 to 2025-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%
- Borrow fee: 75.0 bps annualized
- Shortable universe: 18 configured symbols
- Locate history: not configured

## Data Integrity

- Source: `yahoo`
- Universe source: `static`
- Membership rows: 20
- Requested symbols: 20
- Observed symbols: 20
- Date rows: 1507
- Panel rows: 30140
- Point-in-time universe: no
- Survivorship-bias-free: no
- Corporate actions institutional-grade: no

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| MSFT | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NVDA | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMZN | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| META | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GOOGL | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AVGO | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| COST | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TSLA | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NFLX | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMD | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| ADBE | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CSCO | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| QCOM | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TXN | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| INTU | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMAT | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HON | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| SBUX | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BKNG | 1507 | 100.00% | 0 | 0 | 0 | 0 | 0 |

Warnings:
- Yahoo Finance is a demo source and does not provide an institutional point-in-time research dataset.
- Universe membership is not marked point-in-time; survivorship or lookahead bias may remain.
- Universe is not marked survivorship-bias-free.
- Corporate-action handling is not marked institutional-grade.

## Hypothesis

Assets with stronger recent momentum and lower realized risk should outperform over the next 5 trading days.

Expected direction: positive exposure to [momentum_20d, momentum_60d], negative exposure to [volatility_20d, drawdown_20d].

## Signal

Positive factors: momentum_20d, momentum_60d

Negative factors: volatility_20d, drawdown_20d

Signal is built from cross-sectional percentile ranks so each rebalance compares assets only against the active universe on that date.

## Factor Diagnostics

| Factor | Observations | Coverage | Missing Rate |
| --- | ---: | ---: | ---: |
| momentum_20d | 29740 | 98.67% | 1.33% |
| momentum_60d | 28940 | 96.02% | 3.98% |
| volatility_20d | 29740 | 98.67% | 1.33% |
| drawdown_20d | 29760 | 98.74% | 1.26% |
| reversal_5d | 30040 | 99.67% | 0.33% |

No selected factor pairs exceeded absolute Spearman correlation of 0.75.

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0209 | 0.23 | -30.68% | 1.73 | 0.17% | 11.58% |
| Test | 0.0148 | 0.69 | -15.67% | 1.60 | 0.15% | 10.18% |
| Holdout | -0.0248 | -0.94 | -26.31% | 1.66 | 0.15% | -22.31% |
| Full | 0.0123 | 0.09 | -35.43% | 1.70 | 0.16% | -5.35% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.09% | 0.08% | 0.08% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.04% | 0.02% | 0.03% |
| Avg borrow cost | 0.01% | 0.01% | 0.01% |
| Avg total cost | 0.17% | 0.15% | 0.16% |
| Cumulative cost | 34.88% | 6.04% | 47.66% |
| Avg trade participation | 0.20% | 0.13% | 0.18% |
| Max trade participation | 1.51% | 0.69% | 1.51% |

## Borrow Availability

No date-aware locate or borrow availability history was configured.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 50.00% |
| Avg single-name max weight | 28.87% |
| Avg effective positions | 7.71 |
| Min effective positions | 5.33 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 7 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | 0.74 | 11.02% | 0.13% | 0.00% | 0.01% | 0.07% | 0 | yes |
| 5,000,000 | 0.72 | 10.65% | 0.14% | 0.01% | 0.06% | 0.35% | 0 | yes |
| 10,000,000 | 0.69 | 10.18% | 0.15% | 0.02% | 0.13% | 0.69% | 0 | yes |
| 25,000,000 | 0.61 | 8.78% | 0.18% | 0.05% | 0.31% | 1.74% | 0 | yes |

Estimated capacity: 25,000,000 notional under configured gates.

Warnings:
- Position concentration breached 35% on 7 rebalance dates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | 0.47 | -1.70 | 2.86 | 65.00% |
| Test IC | 0.0148 | -0.0575 | 0.0892 | 64.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q15 | 3 | 15% | 1.00 | -0.0037 | 0.46 | 0.16% | 3.92% |
| h3_q20 | 3 | 20% | 1.00 | -0.0037 | -0.88 | 0.14% | -8.00% |
| h3_q30 | 3 | 30% | 1.00 | -0.0037 | -0.91 | 0.12% | -7.55% |
| h5_q15 | 5 | 15% | 1.00 | 0.0148 | 0.47 | 0.17% | 7.01% |
| h5_q20 | 5 | 20% | 1.00 | 0.0148 | 0.69 | 0.15% | 10.18% |
| h5_q30 | 5 | 30% | 1.00 | 0.0148 | 0.39 | 0.12% | 4.43% |
| h10_q15 | 10 | 15% | 1.00 | 0.0063 | 0.07 | 0.19% | -2.01% |
| h10_q20 | 10 | 20% | 1.00 | 0.0063 | -0.18 | 0.16% | -10.93% |
| h10_q30 | 10 | 30% | 1.00 | 0.0063 | 0.17 | 0.14% | 2.31% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 20% | 0.50 | 0.0148 | 0.88 | 0.07% | 13.55% |
| cost_1x | 5 | 20% | 1.00 | 0.0148 | 0.69 | 0.15% | 10.18% |
| cost_2x | 5 | 20% | 2.00 | 0.0148 | 0.32 | 0.29% | 3.71% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0148 | 0.69 | -15.67% | 1.60 | 0.15% | 10.18% |
| momentum_20d_only | -0.0588 | -1.76 | -33.93% | 1.84 | 0.17% | -34.49% |
| low_volatility_only | 0.0089 | -0.68 | -25.22% | 1.06 | 0.11% | -16.72% |
| reversal_5d_only | 0.0452 | 0.39 | -23.45% | 3.30 | 0.31% | 5.89% |
| random_cross_section | -0.0224 | -1.99 | -30.68% | 3.17 | 0.30% | -29.65% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | -0.0038 | 0.10 | -13.70% | 1.56 | 0.14% | 0.05% |
| liquidity_top_80pct | 0.0309 | 0.59 | -18.68% | 1.48 | 0.13% | 8.54% |
| sector_neutral_liquidity_top_80pct | 0.0021 | 0.43 | -11.26% | 1.55 | 0.14% | 5.70% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-02-23 | 2022-03-02 to 2023-02-14 | 49 | -0.0082 | 0.04 | 0.15% | 48.98% | -3.21% |
| wf_02 | 2023-02-14 | 2023-02-22 to 2024-02-06 | 49 | 0.0052 | -0.08 | 0.19% | 46.94% | -3.87% |
| wf_03 | 2024-02-06 | 2024-02-13 to 2025-01-29 | 49 | 0.0374 | 1.14 | 0.15% | 53.06% | 25.19% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0115 | 0.36 | 0.16% | 66.67% | -3.21% |
| momentum_20d_only | 3 | -0.0142 | -0.56 | 0.17% | 33.33% | -11.84% |
| low_volatility_only | 3 | -0.0103 | -1.53 | 0.10% | 33.33% | -25.97% |
| reversal_5d_only | 3 | 0.0003 | -0.76 | 0.31% | 33.33% | -22.43% |
| random_cross_section | 3 | -0.0067 | -1.84 | 0.32% | 33.33% | -30.32% |
| sector_neutral_signal | 3 | 0.0065 | -0.08 | 0.15% | 66.67% | -4.43% |
| liquidity_top_80pct | 3 | 0.0147 | 0.25 | 0.15% | 66.67% | 0.23% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0002 | -0.10 | 0.14% | 33.33% | 5.63% |

## Research Validity Gate

Verdict: `REJECT`
Gate enabled: yes
Train ends: `2024-04-04`
Validation starts: `2024-04-11`
Holdout starts: `2025-02-12`
FDR alpha: 0.10

| Candidate | Family | Holdout Obs | Holdout IC | Holdout Sharpe | Holdout Return | p-value | FDR q-value |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | primary | 44 | -0.0248 | -0.94 | -22.31% | 0.6837 | 0.8821 |
| low_volatility_only | baseline | 44 | -0.0633 | -1.72 | -43.67% | 0.8852 | 0.8852 |
| momentum_20d_only | baseline | 44 | -0.0336 | 0.10 | -0.98% | 0.7632 | 0.8821 |
| random_cross_section | baseline | 44 | 0.0213 | -0.76 | -12.86% | 0.2447 | 0.8821 |
| reversal_5d_only | baseline | 44 | 0.0847 | 0.68 | 13.02% | 0.0221 | 0.4418 |
| liquidity_top_80pct | stress_test | 44 | -0.0148 | -0.61 | -17.17% | 0.6074 | 0.8821 |
| sector_neutral_liquidity_top_80pct | stress_test | 44 | 0.0045 | -0.10 | -4.94% | 0.4620 | 0.8821 |
| sector_neutral_signal | stress_test | 44 | -0.0107 | -0.39 | -9.99% | 0.5955 | 0.8821 |
| h3_q15 | parameter_sensitivity | 44 | 0.0045 | -0.54 | -10.13% | 0.4649 | 0.8821 |
| h3_q20 | parameter_sensitivity | 44 | 0.0045 | -0.73 | -10.84% | 0.4649 | 0.8821 |
| h3_q30 | parameter_sensitivity | 44 | 0.0045 | -0.17 | -3.48% | 0.4649 | 0.8821 |
| h5_q15 | parameter_sensitivity | 44 | -0.0248 | -0.50 | -16.95% | 0.6837 | 0.8821 |
| h5_q20 | parameter_sensitivity | 44 | -0.0248 | -0.94 | -22.31% | 0.6837 | 0.8821 |
| h5_q30 | parameter_sensitivity | 44 | -0.0248 | -0.56 | -13.43% | 0.6837 | 0.8821 |
| h10_q15 | parameter_sensitivity | 44 | -0.0460 | -0.62 | -32.62% | 0.8380 | 0.8821 |
| h10_q20 | parameter_sensitivity | 44 | -0.0460 | -0.97 | -36.27% | 0.8380 | 0.8821 |
| h10_q30 | parameter_sensitivity | 44 | -0.0460 | -0.54 | -21.20% | 0.8380 | 0.8821 |
| cost_0.5x | cost_sensitivity | 44 | -0.0248 | -0.79 | -19.68% | 0.6837 | 0.8821 |
| cost_1x | cost_sensitivity | 44 | -0.0248 | -0.94 | -22.31% | 0.6837 | 0.8821 |
| cost_2x | cost_sensitivity | 44 | -0.0248 | -1.22 | -27.32% | 0.6837 | 0.8821 |

| Check | Required | Status | Observed | Threshold | Reason |
| --- | --- | --- | ---: | --- | --- |
| positive_holdout_sharpe | yes | fail | -0.9354 | 0.0000 | Holdout Sharpe -0.9354 must be greater than 0.0000. |
| positive_holdout_ic | yes | fail | -0.0248 | 0.0000 | Holdout IC -0.0248 must be greater than 0.0000. |
| fdr_significant | yes | fail | 0.8821 | 0.1000 | Agent FDR q-value 0.8821 must be at most 0.1000. |
| positive_holdout_return | yes | fail | -0.2231 | 0.0000 | Holdout total return -0.2231 must be positive. |
| beats_best_baseline | yes | fail | -0.9354 | 0.6780 | Agent holdout Sharpe -0.9354 must be at least best baseline 0.6780. |
| walk_forward_stable | yes | pass | 0.6667 | >= 50% non-negative Sharpe windows | At least half of walk-forward windows must have non-negative Sharpe. |
| data_ready | yes | fail | no | yes | Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted. |

Reasons preventing promotion:
- Holdout Sharpe -0.9354 must be greater than 0.0000.
- Holdout IC -0.0248 must be greater than 0.0000.
- Agent FDR q-value 0.8821 must be at most 0.1000.
- Holdout total return -0.2231 must be positive.
- Agent holdout Sharpe -0.9354 must be at least best baseline 0.6780.
- Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted.

## Interpretation

The research validity gate rejects promotion even though validation IC and Sharpe are positive. Use the failed holdout or FDR checks as the next iteration target.

The agent signal has the strongest out-of-sample Sharpe among configured strategies. Its test IC is 0.0148, so the next validation target is stability across real data and walk-forward windows.

The signal keeps positive test IC and Sharpe under these stress tests: liquidity_top_80pct, sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics did not flag high pairwise redundancy among selected exposures.

Robustness diagnostics do not flag a major overfit warning under the configured bootstrap and sensitivity checks.

Capacity diagnostics estimate that the signal passes configured gates up to 25,000,000 notional. Treat this as a research approximation because the model uses average dollar volume, not live order book depth.

Walk-forward validation is not yet stable enough for promotion: inspect the weak windows before adding factor complexity.

The train/validation/holdout split is chronological. Validation-period results remain compatibility `test` metrics; holdout-period results drive the research validity gate.

## Limitations

- Synthetic data is useful for deterministic validation but is not investment evidence.
- Stress tests are diagnostics; the primary portfolio remains a simple long-short ranking portfolio.
- Transaction costs and borrow costs are research approximations, not broker execution or securities-lending records.
- Snapshot manifests validate reproducibility and provenance, but they are not a substitute for direct vendor entitlements or independent data audits.

## Next Experiments

- Run the same signal on Yahoo Finance data for a real equity universe.
- Replace redundant factors or orthogonalize correlated exposures before combining signals.
- Add direct vendor data integration that writes validated snapshot manifests.
- Compare this factor against pure momentum, pure low volatility, and reversal baselines.

## Run Reproducibility

- Run ID: `yahoo-nasdaq-momentum-low-volatility-20260618T041314Z-29ccb5e174-5d916c9f`
- Generated at: `2026-06-18T04:13:14Z`
- Config SHA-256: `29ccb5e174e5f14d9e9f9a5977649de87202d59f28d4500d61dc784c1660e62a`
- Git commit: `b6fdb3335b192e2346cc796fdca128c8e83668f3`
- Git branch: `codex/us-026-research-validity`
- Git dirty: yes
- Manifest: `results/runs/yahoo-nasdaq-momentum-low-volatility-20260618T041314Z-29ccb5e174-5d916c9f/manifest.json`
- Frozen config: `results/runs/yahoo-nasdaq-momentum-low-volatility-20260618T041314Z-29ccb5e174-5d916c9f/config.yaml`
