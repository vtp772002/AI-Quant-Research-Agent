# AI Quant Research Report

## Experiment

- Name: `point_in_time_synthetic_momentum_low_volatility`
- Universe: 20 assets from `synthetic`
- Date range: 2020-01-01 to 2024-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%
- Borrow fee: 75.0 bps annualized
- Shortable universe: 18 configured symbols
- Locate history: not configured

## Data Integrity

- Source: `synthetic`
- Universe source: `csv:configs/universe_membership_demo.csv`
- Membership rows: 20
- Requested symbols: 20
- Observed symbols: 20
- Date rows: 1305
- Panel rows: 25576
- Point-in-time universe: yes
- Survivorship-bias-free: yes
- Corporate actions institutional-grade: no

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| ADBE | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMAT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMD | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMZN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AVGO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BKNG | 1043 | 79.92% | 262 | 0 | 0 | 0 | 0 |
| COST | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CSCO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GOOGL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HON | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| INTU | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| META | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| MSFT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NFLX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NVDA | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| QCOM | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| SBUX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TSLA | 1043 | 79.92% | 262 | 0 | 0 | 0 | 0 |
| TXN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |

Warnings:
- Synthetic data validates mechanics but is not investment evidence.
- Corporate-action handling is not marked institutional-grade.
- BKNG coverage is 79.92%; inspect missing rows before trusting results.
- TSLA coverage is 79.92%; inspect missing rows before trusting results.

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
| momentum_20d | 25176 | 96.46% | 3.54% |
| momentum_60d | 24376 | 93.39% | 6.61% |
| volatility_20d | 25176 | 96.46% | 3.54% |
| drawdown_20d | 25196 | 96.54% | 3.46% |
| reversal_5d | 25476 | 97.61% | 2.39% |

Pairs above absolute Spearman correlation of 0.75:

| Factor A | Factor B | Spearman Corr |
| --- | --- | ---: |
| momentum_20d | drawdown_20d | 0.7897 |

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0175 | 0.24 | -32.27% | 1.53 | 0.18% | 10.89% |
| Test | 0.0223 | -1.28 | -25.50% | 1.66 | 0.22% | -19.20% |
| Holdout | 0.0207 | 0.80 | -10.42% | 1.21 | 0.16% | 9.88% |
| Full | 0.0204 | 0.18 | -32.27% | 1.50 | 0.18% | 7.38% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.08% | 0.07% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.06% | 0.09% | 0.06% |
| Avg borrow cost | 0.01% | 0.01% | 0.01% |
| Avg total cost | 0.18% | 0.22% | 0.18% |
| Cumulative cost | 31.47% | 7.86% | 45.75% |
| Avg trade participation | 0.38% | 0.55% | 0.43% |
| Max trade participation | 2.10% | 2.71% | 2.71% |

## Borrow Availability

No date-aware locate or borrow availability history was configured.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 33.33% |
| Avg single-name max weight | 25.99% |
| Avg effective positions | 8.08 |
| Min effective positions | 6.86 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 0 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | -1.09 | -16.77% | 0.14% | 0.01% | 0.06% | 0.27% | 0 | no |
| 5,000,000 | -1.18 | -17.86% | 0.18% | 0.05% | 0.28% | 1.36% | 0 | no |
| 10,000,000 | -1.28 | -19.20% | 0.22% | 0.09% | 0.55% | 2.71% | 0 | no |
| 25,000,000 | -1.60 | -23.09% | 0.36% | 0.23% | 1.38% | 6.78% | 0 | no |

Warnings:
- No configured notional passed both participation and positive-Sharpe capacity gates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | -0.66 | -3.33 | 1.86 | 28.50% |
| Test IC | 0.0328 | -0.0345 | 0.0951 | 82.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q15 | 3 | 15% | 1.00 | 0.0158 | -1.65 | 0.26% | -19.67% |
| h3_q20 | 3 | 20% | 1.00 | 0.0158 | -1.73 | 0.22% | -17.55% |
| h3_q30 | 3 | 30% | 1.00 | 0.0158 | -1.88 | 0.16% | -14.52% |
| h5_q15 | 5 | 15% | 1.00 | 0.0223 | -1.13 | 0.27% | -21.97% |
| h5_q20 | 5 | 20% | 1.00 | 0.0223 | -1.28 | 0.22% | -19.20% |
| h5_q30 | 5 | 30% | 1.00 | 0.0223 | -1.13 | 0.17% | -13.10% |
| h10_q15 | 10 | 15% | 1.00 | 0.0090 | -0.53 | 0.30% | -22.44% |
| h10_q20 | 10 | 20% | 1.00 | 0.0090 | 0.07 | 0.24% | -1.37% |
| h10_q30 | 10 | 30% | 1.00 | 0.0090 | -0.26 | 0.18% | -6.24% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 20% | 0.50 | 0.0223 | -1.03 | 0.11% | -15.94% |
| cost_1x | 5 | 20% | 1.00 | 0.0223 | -1.28 | 0.22% | -19.20% |
| cost_2x | 5 | 20% | 2.00 | 0.0223 | -1.79 | 0.45% | -25.36% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0223 | -1.28 | -25.50% | 1.66 | 0.22% | -19.20% |
| momentum_20d_only | -0.0038 | -1.73 | -32.18% | 1.96 | 0.27% | -29.33% |
| low_volatility_only | -0.0346 | -2.39 | -39.31% | 0.99 | 0.14% | -32.23% |
| reversal_5d_only | 0.0197 | -0.38 | -12.18% | 3.17 | 0.46% | -6.08% |
| random_cross_section | -0.0352 | -2.03 | -36.10% | 3.32 | 0.46% | -34.97% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0471 | 0.20 | -18.92% | 1.55 | 0.21% | 1.38% |
| liquidity_top_80pct | 0.0319 | -0.37 | -19.41% | 1.64 | 0.20% | -6.06% |
| sector_neutral_liquidity_top_80pct | 0.0662 | 0.30 | -18.20% | 1.51 | 0.19% | 3.01% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2021-10-20 | 2021-10-27 to 2022-08-10 | 42 | 0.0046 | -0.23 | 0.18% | 50.00% | -7.53% |
| wf_02 | 2022-08-10 | 2022-08-17 to 2023-05-31 | 42 | 0.0345 | 0.63 | 0.19% | 59.52% | 10.90% |
| wf_03 | 2023-05-31 | 2023-06-07 to 2024-03-20 | 42 | 0.0252 | -0.61 | 0.22% | 40.48% | -12.16% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0214 | -0.07 | 0.19% | 100.00% | -7.53% |
| momentum_20d_only | 3 | -0.0038 | -0.82 | 0.22% | 33.33% | -18.13% |
| low_volatility_only | 3 | -0.0034 | -0.79 | 0.14% | 33.33% | -9.09% |
| reversal_5d_only | 3 | -0.0020 | -1.40 | 0.43% | 66.67% | -21.05% |
| random_cross_section | 3 | 0.0086 | -0.24 | 0.43% | 66.67% | -6.28% |
| sector_neutral_signal | 3 | 0.0289 | 0.24 | 0.20% | 66.67% | -2.30% |
| liquidity_top_80pct | 3 | 0.0288 | 0.34 | 0.17% | 100.00% | 4.26% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0318 | 0.37 | 0.17% | 100.00% | 1.33% |

## Research Validity Gate

Verdict: `REJECT`
Gate enabled: yes
Train ends: `2023-07-19`
Validation starts: `2023-07-26`
Holdout starts: `2024-04-03`
FDR alpha: 0.10

| Candidate | Family | Holdout Obs | Holdout IC | Holdout Sharpe | Holdout Return | p-value | FDR q-value |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | primary | 38 | 0.0207 | 0.80 | 9.88% | 0.2872 | 0.4881 |
| low_volatility_only | baseline | 38 | -0.0254 | -1.28 | -19.24% | 0.7706 | 0.8112 |
| momentum_20d_only | baseline | 38 | 0.0821 | 1.96 | 36.49% | 0.0130 | 0.2609 |
| random_cross_section | baseline | 38 | 0.0151 | 0.47 | 6.87% | 0.3763 | 0.4881 |
| reversal_5d_only | baseline | 38 | -0.1365 | -4.49 | -56.70% | 0.9999 | 0.9999 |
| liquidity_top_80pct | stress_test | 38 | 0.0116 | -0.01 | -1.24% | 0.3905 | 0.4881 |
| sector_neutral_liquidity_top_80pct | stress_test | 38 | -0.0022 | 0.38 | 4.44% | 0.5204 | 0.5782 |
| sector_neutral_signal | stress_test | 38 | 0.0045 | -0.01 | -1.89% | 0.4560 | 0.5365 |
| h3_q15 | parameter_sensitivity | 38 | 0.0129 | -0.17 | -2.97% | 0.3563 | 0.4881 |
| h3_q20 | parameter_sensitivity | 38 | 0.0129 | -0.41 | -4.52% | 0.3563 | 0.4881 |
| h3_q30 | parameter_sensitivity | 38 | 0.0129 | -1.27 | -8.81% | 0.3563 | 0.4881 |
| h5_q15 | parameter_sensitivity | 38 | 0.0207 | 1.35 | 21.62% | 0.2872 | 0.4881 |
| h5_q20 | parameter_sensitivity | 38 | 0.0207 | 0.80 | 9.88% | 0.2872 | 0.4881 |
| h5_q30 | parameter_sensitivity | 38 | 0.0207 | -0.14 | -2.74% | 0.2872 | 0.4881 |
| h10_q15 | parameter_sensitivity | 38 | 0.0136 | 1.19 | 49.98% | 0.3865 | 0.4881 |
| h10_q20 | parameter_sensitivity | 38 | 0.0136 | 0.57 | 17.46% | 0.3865 | 0.4881 |
| h10_q30 | parameter_sensitivity | 38 | 0.0136 | -0.14 | -7.20% | 0.3865 | 0.4881 |
| cost_0.5x | cost_sensitivity | 38 | 0.0207 | 1.03 | 13.36% | 0.2872 | 0.4881 |
| cost_1x | cost_sensitivity | 38 | 0.0207 | 0.80 | 9.88% | 0.2872 | 0.4881 |
| cost_2x | cost_sensitivity | 38 | 0.0207 | 0.33 | 3.22% | 0.2872 | 0.4881 |

| Check | Required | Status | Observed | Threshold | Reason |
| --- | --- | --- | ---: | --- | --- |
| positive_holdout_sharpe | yes | pass | 0.7965 | 0.0000 | Holdout Sharpe 0.7965 must be greater than 0.0000. |
| positive_holdout_ic | yes | pass | 0.0207 | 0.0000 | Holdout IC 0.0207 must be greater than 0.0000. |
| fdr_significant | yes | fail | 0.4881 | 0.1000 | Agent FDR q-value 0.4881 must be at most 0.1000. |
| positive_holdout_return | yes | pass | 0.0988 | 0.0000 | Holdout total return 0.0988 must be positive. |
| beats_best_baseline | yes | fail | 0.7965 | 1.9569 | Agent holdout Sharpe 0.7965 must be at least best baseline 1.9569. |
| walk_forward_stable | yes | fail | 0.3333 | >= 50% non-negative Sharpe windows | At least half of walk-forward windows must have non-negative Sharpe. |
| data_ready | yes | fail | no | yes | Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted. |

Reasons preventing promotion:
- Agent FDR q-value 0.4881 must be at most 0.1000.
- Agent holdout Sharpe 0.7965 must be at least best baseline 1.9569.
- At least half of walk-forward windows must have non-negative Sharpe.
- Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted.

## Interpretation

The research validity gate rejects promotion. The signal shows positive validation rank correlation but weak portfolio conversion. Investigate turnover, concentration, and whether the long/short cutoffs are too aggressive.

The strongest out-of-sample Sharpe is from `reversal_5d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The signal keeps positive test IC and Sharpe under these stress tests: sector_neutral_signal, sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.7897; simplify or orthogonalize before adding more factors.

Robustness diagnostics flag caution: bootstrap Sharpe confidence is weak; parameter sensitivity is fragile; high-cost sensitivity erases positive Sharpe.

Capacity diagnostics do not identify a configured notional that passes both participation and positive-Sharpe gates.

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

- Run ID: `point-in-time-synthetic-momentum-low-volatility-20260618T041258Z-6ee91feaff-9ecc3dc6`
- Generated at: `2026-06-18T04:12:58Z`
- Config SHA-256: `6ee91feaff9f41c16154e2f88aeb2394dddb875ae7d434410eb194290871ef29`
- Git commit: `b6fdb3335b192e2346cc796fdca128c8e83668f3`
- Git branch: `codex/us-026-research-validity`
- Git dirty: yes
- Manifest: `results/runs/point-in-time-synthetic-momentum-low-volatility-20260618T041258Z-6ee91feaff-9ecc3dc6/manifest.json`
- Frozen config: `results/runs/point-in-time-synthetic-momentum-low-volatility-20260618T041258Z-6ee91feaff-9ecc3dc6/config.yaml`
