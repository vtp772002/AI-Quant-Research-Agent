# AI Quant Research Report

## Experiment

- Name: `momentum_low_volatility_demo`
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
- Universe source: `static`
- Membership rows: 20
- Requested symbols: 20
- Observed symbols: 20
- Date rows: 1305
- Panel rows: 26100
- Point-in-time universe: no
- Survivorship-bias-free: no
- Corporate actions institutional-grade: no

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| MSFT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NVDA | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMZN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| META | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GOOGL | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AVGO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| COST | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TSLA | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| NFLX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMD | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| ADBE | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CSCO | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| QCOM | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| TXN | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| INTU | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| AMAT | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HON | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| SBUX | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BKNG | 1305 | 100.00% | 0 | 0 | 0 | 0 | 0 |

Warnings:
- Synthetic data validates mechanics but is not investment evidence.
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
| momentum_20d | 25700 | 98.47% | 1.53% |
| momentum_60d | 24900 | 95.40% | 4.60% |
| volatility_20d | 25700 | 98.47% | 1.53% |
| drawdown_20d | 25720 | 98.54% | 1.46% |
| reversal_5d | 26000 | 99.62% | 0.38% |

Pairs above absolute Spearman correlation of 0.75:

| Factor A | Factor B | Spearman Corr |
| --- | --- | ---: |
| momentum_20d | drawdown_20d | 0.7881 |

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0186 | 0.16 | -34.06% | 1.57 | 0.18% | 4.05% |
| Test | 0.0144 | -1.37 | -25.95% | 1.57 | 0.20% | -17.97% |
| Holdout | 0.0233 | 0.53 | -11.66% | 1.31 | 0.18% | 6.15% |
| Full | 0.0206 | 0.09 | -34.06% | 1.53 | 0.19% | -1.83% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.08% | 0.08% |
| Avg spread cost | 0.03% | 0.03% | 0.03% |
| Avg impact cost | 0.06% | 0.08% | 0.06% |
| Avg borrow cost | 0.01% | 0.01% | 0.01% |
| Avg total cost | 0.18% | 0.20% | 0.19% |
| Cumulative cost | 32.11% | 7.12% | 46.23% |
| Avg trade participation | 0.38% | 0.50% | 0.42% |
| Max trade participation | 2.44% | 3.01% | 3.01% |

## Borrow Availability

No date-aware locate or borrow availability history was configured.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 33.33% |
| Avg single-name max weight | 25.99% |
| Avg effective positions | 8.13 |
| Min effective positions | 6.86 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 0 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | -1.19 | -15.88% | 0.13% | 0.01% | 0.05% | 0.30% | 0 | no |
| 5,000,000 | -1.27 | -16.82% | 0.16% | 0.04% | 0.25% | 1.51% | 0 | no |
| 10,000,000 | -1.37 | -17.97% | 0.20% | 0.08% | 0.50% | 3.01% | 0 | no |
| 25,000,000 | -1.66 | -21.34% | 0.32% | 0.20% | 1.25% | 7.53% | 0 | no |

Warnings:
- No configured notional passed both participation and positive-Sharpe capacity gates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | -0.74 | -3.12 | 1.45 | 28.00% |
| Test IC | 0.0262 | -0.0398 | 0.0859 | 80.00% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q15 | 3 | 15% | 1.00 | 0.0101 | -2.43 | 0.24% | -25.08% |
| h3_q20 | 3 | 20% | 1.00 | 0.0101 | -2.01 | 0.20% | -18.26% |
| h3_q30 | 3 | 30% | 1.00 | 0.0101 | -1.13 | 0.15% | -8.99% |
| h5_q15 | 5 | 15% | 1.00 | 0.0144 | -1.61 | 0.24% | -27.17% |
| h5_q20 | 5 | 20% | 1.00 | 0.0144 | -1.37 | 0.20% | -17.97% |
| h5_q30 | 5 | 30% | 1.00 | 0.0144 | -0.70 | 0.16% | -7.93% |
| h10_q15 | 10 | 15% | 1.00 | 0.0012 | -0.56 | 0.27% | -23.24% |
| h10_q20 | 10 | 20% | 1.00 | 0.0012 | 0.06 | 0.22% | -1.61% |
| h10_q30 | 10 | 30% | 1.00 | 0.0012 | 0.12 | 0.18% | 1.05% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 20% | 0.50 | 0.0144 | -1.11 | 0.10% | -14.97% |
| cost_1x | 5 | 20% | 1.00 | 0.0144 | -1.37 | 0.20% | -17.97% |
| cost_2x | 5 | 20% | 2.00 | 0.0144 | -1.87 | 0.41% | -23.67% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.0144 | -1.37 | -25.95% | 1.57 | 0.20% | -17.97% |
| momentum_20d_only | -0.0078 | -1.57 | -28.22% | 1.89 | 0.26% | -25.38% |
| low_volatility_only | -0.0373 | -2.40 | -40.01% | 0.99 | 0.14% | -33.00% |
| reversal_5d_only | 0.0214 | -0.51 | -13.74% | 3.20 | 0.48% | -7.92% |
| random_cross_section | -0.0245 | -1.79 | -27.30% | 3.09 | 0.43% | -22.09% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0247 | -0.26 | -23.47% | 1.39 | 0.20% | -6.17% |
| liquidity_top_80pct | 0.0233 | -0.35 | -19.70% | 1.60 | 0.20% | -5.37% |
| sector_neutral_liquidity_top_80pct | 0.0623 | 0.56 | -14.09% | 1.31 | 0.16% | 7.30% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2021-10-20 | 2021-10-27 to 2022-08-10 | 42 | 0.0046 | -0.17 | 0.17% | 50.00% | -6.30% |
| wf_02 | 2022-08-10 | 2022-08-17 to 2023-05-31 | 42 | 0.0345 | 0.58 | 0.20% | 59.52% | 9.82% |
| wf_03 | 2023-05-31 | 2023-06-07 to 2024-03-20 | 42 | 0.0185 | -0.62 | 0.20% | 38.10% | -11.22% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0192 | -0.07 | 0.19% | 100.00% | -6.30% |
| momentum_20d_only | 3 | -0.0049 | -0.60 | 0.21% | 0.00% | -13.19% |
| low_volatility_only | 3 | -0.0042 | -0.85 | 0.14% | 33.33% | -9.31% |
| reversal_5d_only | 3 | -0.0016 | -1.55 | 0.43% | 66.67% | -24.43% |
| random_cross_section | 3 | 0.0055 | -1.15 | 0.44% | 66.67% | -20.21% |
| sector_neutral_signal | 3 | 0.0159 | -0.04 | 0.19% | 66.67% | -1.95% |
| liquidity_top_80pct | 3 | 0.0265 | 0.45 | 0.17% | 100.00% | 6.56% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0307 | 0.16 | 0.16% | 100.00% | -3.43% |

## Research Validity Gate

Verdict: `REJECT`
Gate enabled: yes
Train ends: `2023-07-19`
Validation starts: `2023-07-26`
Holdout starts: `2024-04-03`
FDR alpha: 0.10

| Candidate | Family | Holdout Obs | Holdout IC | Holdout Sharpe | Holdout Return | p-value | FDR q-value |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | primary | 38 | 0.0233 | 0.53 | 6.15% | 0.2549 | 0.4261 |
| low_volatility_only | baseline | 38 | -0.0254 | -0.79 | -12.63% | 0.7701 | 0.8557 |
| momentum_20d_only | baseline | 38 | 0.0765 | 1.91 | 37.29% | 0.0204 | 0.4071 |
| random_cross_section | baseline | 38 | -0.0591 | -2.22 | -36.69% | 0.9295 | 0.9784 |
| reversal_5d_only | baseline | 38 | -0.1259 | -4.84 | -59.29% | 0.9996 | 0.9996 |
| liquidity_top_80pct | stress_test | 38 | 0.0139 | 0.77 | 9.13% | 0.3634 | 0.4543 |
| sector_neutral_liquidity_top_80pct | stress_test | 38 | 0.0209 | 1.25 | 22.73% | 0.3196 | 0.4261 |
| sector_neutral_signal | stress_test | 38 | 0.0101 | 0.15 | 0.84% | 0.4012 | 0.4720 |
| h3_q15 | parameter_sensitivity | 38 | 0.0169 | -0.69 | -8.13% | 0.3120 | 0.4261 |
| h3_q20 | parameter_sensitivity | 38 | 0.0169 | -0.69 | -7.65% | 0.3120 | 0.4261 |
| h3_q30 | parameter_sensitivity | 38 | 0.0169 | -0.66 | -5.21% | 0.3120 | 0.4261 |
| h5_q15 | parameter_sensitivity | 38 | 0.0233 | 0.42 | 4.93% | 0.2549 | 0.4261 |
| h5_q20 | parameter_sensitivity | 38 | 0.0233 | 0.53 | 6.15% | 0.2549 | 0.4261 |
| h5_q30 | parameter_sensitivity | 38 | 0.0233 | 0.35 | 3.34% | 0.2549 | 0.4261 |
| h10_q15 | parameter_sensitivity | 38 | 0.0219 | 0.68 | 23.11% | 0.3161 | 0.4261 |
| h10_q20 | parameter_sensitivity | 38 | 0.0219 | 0.58 | 16.65% | 0.3161 | 0.4261 |
| h10_q30 | parameter_sensitivity | 38 | 0.0219 | 0.40 | 10.14% | 0.3161 | 0.4261 |
| cost_0.5x | cost_sensitivity | 38 | 0.0233 | 0.78 | 9.81% | 0.2549 | 0.4261 |
| cost_1x | cost_sensitivity | 38 | 0.0233 | 0.53 | 6.15% | 0.2549 | 0.4261 |
| cost_2x | cost_sensitivity | 38 | 0.0233 | 0.03 | -0.83% | 0.2549 | 0.4261 |

| Check | Required | Status | Observed | Threshold | Reason |
| --- | --- | --- | ---: | --- | --- |
| positive_holdout_sharpe | yes | pass | 0.5308 | 0.0000 | Holdout Sharpe 0.5308 must be greater than 0.0000. |
| positive_holdout_ic | yes | pass | 0.0233 | 0.0000 | Holdout IC 0.0233 must be greater than 0.0000. |
| fdr_significant | yes | fail | 0.4261 | 0.1000 | Agent FDR q-value 0.4261 must be at most 0.1000. |
| positive_holdout_return | yes | pass | 0.0615 | 0.0000 | Holdout total return 0.0615 must be positive. |
| beats_best_baseline | yes | fail | 0.5308 | 1.9062 | Agent holdout Sharpe 0.5308 must be at least best baseline 1.9062. |
| walk_forward_stable | yes | fail | 0.3333 | >= 50% non-negative Sharpe windows | At least half of walk-forward windows must have non-negative Sharpe. |
| data_ready | yes | fail | no | yes | Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted. |

Reasons preventing promotion:
- Agent FDR q-value 0.4261 must be at most 0.1000.
- Agent holdout Sharpe 0.5308 must be at least best baseline 1.9062.
- At least half of walk-forward windows must have non-negative Sharpe.
- Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted.

## Interpretation

The run-level research validity gate rejects promotion. The signal shows positive validation rank correlation but weak portfolio conversion. Investigate turnover, concentration, and whether the long/short cutoffs are too aggressive.

The strongest out-of-sample Sharpe is from `reversal_5d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The signal keeps positive test IC and Sharpe under these stress tests: sector_neutral_liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.7881; simplify or orthogonalize before adding more factors.

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

- Run ID: `momentum-low-volatility-demo-20260618T045501Z-67e8b327e8-120121be`
- Generated at: `2026-06-18T04:55:01Z`
- Config SHA-256: `67e8b327e804ecc0100f93a505a1b5b2a1af10af5d8fccf30a682b486b1bee1f`
- Git commit: `e546d07235344a44eb2eafaaa3757636b8cb1dc6`
- Git branch: `codex/us-027-cross-run-family-controls`
- Git dirty: no
- Manifest: `results/runs/momentum-low-volatility-demo-20260618T045501Z-67e8b327e8-120121be/manifest.json`
- Frozen config: `results/runs/momentum-low-volatility-demo-20260618T045501Z-67e8b327e8-120121be/config.yaml`
