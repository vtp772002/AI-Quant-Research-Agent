# AI Quant Research Report

## Experiment

- Name: `institutional_snapshot_momentum_low_volatility`
- Universe: 8 assets from `csv_snapshot`
- Date range: 2020-01-01 to 2022-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 25%
- Borrow fee: 75.0 bps annualized
- Shortable universe: 6 configured symbols
- Locate history: `configs/../data/golden/borrow_availability_demo.csv`

## Data Integrity

- Source: `csv_snapshot`
- Universe source: `csv:configs/institutional_snapshot_membership_demo.csv`
- Membership rows: 8
- Requested symbols: 8
- Observed symbols: 8
- Date rows: 783
- Panel rows: 6264
- Point-in-time universe: yes
- Survivorship-bias-free: yes
- Corporate actions institutional-grade: yes
- Snapshot dataset: `institutional-golden-demo-v1`
- Snapshot vendor: `InternalGolden`
- Snapshot as-of: `2023-01-03`
- Snapshot manifest: `configs/../data/golden/institutional_ohlcv_snapshot.yaml`
- Snapshot hash valid: yes
- Snapshot row count valid: yes
- Snapshot symbol set valid: yes
- Snapshot date range valid: yes

| Symbol | Observations | Coverage | Missing Rows | Zero Volume | Bad Prices | Extreme Returns | Stale Prices |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAA | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| BBB | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| CCC | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| DDD | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| EEE | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| FFF | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| GGG | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |
| HHH | 783 | 100.00% | 0 | 0 | 0 | 0 | 0 |

No data integrity warnings were detected.

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
| momentum_20d | 6104 | 97.45% | 2.55% |
| momentum_60d | 5784 | 92.34% | 7.66% |
| volatility_20d | 6104 | 97.45% | 2.55% |
| drawdown_20d | 6112 | 97.57% | 2.43% |

Pairs above absolute Spearman correlation of 0.75:

| Factor A | Factor B | Spearman Corr |
| --- | --- | ---: |
| momentum_20d | drawdown_20d | 0.8114 |

## Results

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Avg Cost | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0070 | -0.27 | -35.71% | 1.59 | 0.24% | -23.24% |
| Test | 0.1459 | 1.84 | -12.77% | 2.06 | 0.32% | 19.90% |
| Holdout | -0.0176 | -0.35 | -17.98% | 1.92 | 0.31% | -6.21% |
| Full | 0.0156 | 0.02 | -35.71% | 1.70 | 0.26% | -11.01% |

## Execution Costs

| Component | Train | Test | Full |
| --- | ---: | ---: | ---: |
| Avg base cost | 0.08% | 0.10% | 0.08% |
| Avg spread cost | 0.03% | 0.04% | 0.03% |
| Avg impact cost | 0.09% | 0.13% | 0.10% |
| Avg borrow cost | 0.04% | 0.04% | 0.04% |
| Avg total cost | 0.24% | 0.32% | 0.26% |
| Cumulative cost | 23.12% | 5.75% | 35.63% |
| Avg trade participation | 0.48% | 0.55% | 0.51% |
| Max trade participation | 3.01% | 2.12% | 3.01% |

## Borrow Availability

| Field | Value |
| --- | ---: |
| Rows | 6264 |
| Symbols | 8 |
| Date range | 2020-01-01 to 2022-12-30 |
| Coverage | 100.00% |
| Unavailable rows | 1698 |
| Hard-to-borrow rows | 783 |
| Avg borrow fee | 241.2 bps |
| Max borrow fee | 950.0 bps |

Warnings:
- Borrow availability marks 1698 date-symbol rows as not shortable.
- Borrow availability flags 783 hard-to-borrow rows at or above 500 bps.

## Capacity Diagnostics

| Metric | Value |
| --- | ---: |
| Max single-name weight | 100.00% |
| Avg single-name max weight | 68.75% |
| Avg effective positions | 3.79 |
| Min effective positions | 2.67 |
| Avg gross exposure | 2.00x |
| Max gross exposure | 2.00x |
| Position weight breaches | 133 |

Capacity curve:

| Notional | Test Sharpe | Test Return | Avg Cost | Avg Impact | Avg Participation | Max Participation | Breaches | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | 2.04 | 22.50% | 0.20% | 0.01% | 0.06% | 0.21% | 0 | yes |
| 5,000,000 | 1.95 | 21.34% | 0.25% | 0.07% | 0.28% | 1.06% | 0 | yes |
| 10,000,000 | 1.84 | 19.90% | 0.32% | 0.13% | 0.55% | 2.12% | 0 | yes |
| 25,000,000 | 1.50 | 15.68% | 0.52% | 0.33% | 1.39% | 5.29% | 0 | yes |

Estimated capacity: 25,000,000 notional under configured gates.

Warnings:
- Position concentration breached 35% on 133 rebalance dates.

## Robustness Diagnostics

| Metric | Mean | 2.5% | 97.5% | Positive Probability |
| --- | ---: | ---: | ---: | ---: |
| Test Sharpe | 2.26 | -1.38 | 5.66 | 91.50% |
| Test IC | 0.1447 | 0.0215 | 0.2436 | 98.50% |

Parameter Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| h3_q20 | 3 | 20% | 1.00 | 0.0091 | 1.06 | 0.29% | 7.04% |
| h3_q25 | 3 | 25% | 1.00 | 0.0091 | 1.06 | 0.29% | 7.04% |
| h5_q20 | 5 | 20% | 1.00 | 0.1459 | 1.84 | 0.32% | 19.90% |
| h5_q25 | 5 | 25% | 1.00 | 0.1459 | 1.84 | 0.32% | 19.90% |
| h10_q20 | 10 | 20% | 1.00 | 0.0721 | 0.68 | 0.34% | 11.47% |
| h10_q25 | 10 | 25% | 1.00 | 0.0721 | 0.68 | 0.34% | 11.47% |

Cost Sensitivity:

| Variant | Holding | Quantile | Cost Mult | Test IC | Test Sharpe | Test Cost | Test Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cost_0.5x | 5 | 25% | 0.50 | 0.1459 | 2.11 | 0.16% | 23.37% |
| cost_1x | 5 | 25% | 1.00 | 0.1459 | 1.84 | 0.32% | 19.90% |
| cost_2x | 5 | 25% | 2.00 | 0.1459 | 1.30 | 0.64% | 13.24% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 0.1459 | 1.84 | -12.77% | 2.06 | 0.32% | 19.90% |
| momentum_20d_only | -0.0463 | -2.38 | -34.58% | 1.94 | 0.35% | -31.33% |
| low_volatility_only | 0.0313 | 0.57 | -11.26% | 1.16 | 0.21% | 4.76% |
| random_cross_section | 0.0376 | 0.37 | -13.47% | 3.00 | 0.56% | 2.50% |

## Stress Tests

| Stress Test | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Cost | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_neutral_signal | 0.0848 | -0.65 | -28.14% | 1.60 | 0.26% | -10.17% |
| liquidity_top_80pct | 0.1483 | 1.37 | -13.79% | 2.04 | 0.31% | 11.29% |
| sector_neutral_liquidity_top_80pct | 0.0655 | -1.29 | -23.89% | 1.40 | 0.23% | -12.52% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Avg Cost | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2021-03-03 | 2021-03-10 to 2021-08-11 | 23 | 0.0704 | 2.42 | 0.22% | 52.17% | 37.49% |
| wf_02 | 2021-08-11 | 2021-08-18 to 2022-01-19 | 23 | 0.0022 | -0.47 | 0.25% | 52.17% | -9.48% |
| wf_03 | 2022-01-19 | 2022-01-26 to 2022-06-29 | 23 | 0.1501 | 1.59 | 0.30% | 73.91% | 20.89% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Mean Cost | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0742 | 1.18 | 0.25% | 100.00% | 20.89% |
| momentum_20d_only | 3 | 0.0449 | 1.02 | 0.25% | 66.67% | 39.12% |
| low_volatility_only | 3 | 0.0050 | 0.20 | 0.23% | 66.67% | 5.10% |
| random_cross_section | 3 | 0.0495 | 0.42 | 0.57% | 66.67% | 1.03% |
| sector_neutral_signal | 3 | 0.0482 | 0.01 | 0.27% | 66.67% | -0.26% |
| liquidity_top_80pct | 3 | 0.0846 | 1.52 | 0.23% | 100.00% | 7.89% |
| sector_neutral_liquidity_top_80pct | 3 | 0.0329 | 0.06 | 0.27% | 66.67% | -7.03% |

## Research Validity Gate

Verdict: `REJECT`
Gate enabled: yes
Train ends: `2022-02-23`
Validation starts: `2022-03-02`
Holdout starts: `2022-07-20`
FDR alpha: 0.10

| Candidate | Family | Holdout Obs | Holdout IC | Holdout Sharpe | Holdout Return | p-value | FDR q-value |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_signal | primary | 21 | -0.0176 | -0.35 | -6.21% | 0.5837 | 0.7623 |
| low_volatility_only | baseline | 22 | 0.0238 | -0.28 | -5.13% | 0.3674 | 0.7623 |
| momentum_20d_only | baseline | 21 | 0.0147 | 0.40 | 3.59% | 0.4345 | 0.7623 |
| random_cross_section | baseline | 21 | -0.0612 | -1.85 | -21.42% | 0.7931 | 0.8846 |
| liquidity_top_80pct | stress_test | 20 | 0.0107 | 1.36 | 18.91% | 0.4531 | 0.7623 |
| sector_neutral_liquidity_top_80pct | stress_test | 22 | 0.0335 | 0.43 | 4.21% | 0.3406 | 0.7623 |
| sector_neutral_signal | stress_test | 22 | -0.0248 | -0.53 | -11.61% | 0.6194 | 0.7623 |
| h3_q20 | parameter_sensitivity | 21 | -0.0949 | -3.69 | -25.43% | 0.8846 | 0.8846 |
| h3_q25 | parameter_sensitivity | 21 | -0.0949 | -3.69 | -25.43% | 0.8846 | 0.8846 |
| h5_q20 | parameter_sensitivity | 21 | -0.0176 | -0.35 | -6.21% | 0.5837 | 0.7623 |
| h5_q25 | parameter_sensitivity | 21 | -0.0176 | -0.35 | -6.21% | 0.5837 | 0.7623 |
| h10_q20 | parameter_sensitivity | 21 | -0.0118 | -0.77 | -19.32% | 0.5545 | 0.7623 |
| h10_q25 | parameter_sensitivity | 21 | -0.0118 | -0.77 | -19.32% | 0.5545 | 0.7623 |
| cost_0.5x | cost_sensitivity | 21 | -0.0176 | -0.09 | -3.08% | 0.5837 | 0.7623 |
| cost_1x | cost_sensitivity | 21 | -0.0176 | -0.35 | -6.21% | 0.5837 | 0.7623 |
| cost_2x | cost_sensitivity | 21 | -0.0176 | -0.86 | -12.18% | 0.5837 | 0.7623 |

| Check | Required | Status | Observed | Threshold | Reason |
| --- | --- | --- | ---: | --- | --- |
| positive_holdout_sharpe | yes | fail | -0.3453 | 0.0000 | Holdout Sharpe -0.3453 must be greater than 0.0000. |
| positive_holdout_ic | yes | fail | -0.0176 | 0.0000 | Holdout IC -0.0176 must be greater than 0.0000. |
| fdr_significant | yes | fail | 0.7623 | 0.1000 | Agent FDR q-value 0.7623 must be at most 0.1000. |
| positive_holdout_return | yes | fail | -0.0621 | 0.0000 | Holdout total return -0.0621 must be positive. |
| beats_best_baseline | yes | fail | -0.3453 | 0.3985 | Agent holdout Sharpe -0.3453 must be at least best baseline 0.3985. |
| walk_forward_stable | yes | pass | 0.6667 | >= 50% non-negative Sharpe windows | At least half of walk-forward windows must have non-negative Sharpe. |
| data_ready | yes | pass | yes | yes | Data must be point-in-time, survivorship-bias-free, and corporate-action adjusted. |

Reasons preventing promotion:
- Holdout Sharpe -0.3453 must be greater than 0.0000.
- Holdout IC -0.0176 must be greater than 0.0000.
- Agent FDR q-value 0.7623 must be at most 0.1000.
- Holdout total return -0.0621 must be positive.
- Agent holdout Sharpe -0.3453 must be at least best baseline 0.3985.

## Interpretation

The research validity gate rejects promotion even though validation IC and Sharpe are positive. Use the failed holdout or FDR checks as the next iteration target.

The agent signal has the strongest out-of-sample Sharpe among configured strategies. Its test IC is 0.1459, so the next validation target is stability across real data and walk-forward windows.

The signal keeps positive test IC and Sharpe under these stress tests: liquidity_top_80pct. Compare their drawdowns and turnover before treating this as robust.

Factor diagnostics flagged potentially redundant exposures. The strongest pair is `momentum_20d` and `drawdown_20d` with Spearman correlation 0.8114; simplify or orthogonalize before adding more factors.

Robustness diagnostics do not flag a major overfit warning under the configured bootstrap and sensitivity checks.

Capacity diagnostics estimate that the signal passes configured gates up to 25,000,000 notional. Treat this as a research approximation because the model uses average dollar volume, not live order book depth.

Walk-forward validation supports further research: most agent-signal windows have positive IC and the average window Sharpe is positive.

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

- Run ID: `institutional-snapshot-momentum-low-volatility-20260618T041304Z-04dda700d6-b14c06a5`
- Generated at: `2026-06-18T04:13:04Z`
- Config SHA-256: `04dda700d678d45163686448c7691710d241f3bb9310a3e641bab5db91955f9a`
- Git commit: `b6fdb3335b192e2346cc796fdca128c8e83668f3`
- Git branch: `codex/us-026-research-validity`
- Git dirty: yes
- Manifest: `results/runs/institutional-snapshot-momentum-low-volatility-20260618T041304Z-04dda700d6-b14c06a5/manifest.json`
- Frozen config: `results/runs/institutional-snapshot-momentum-low-volatility-20260618T041304Z-04dda700d6-b14c06a5/config.yaml`
