# AI Quant Research Report

## Experiment

- Name: `yahoo_nasdaq_momentum_low_volatility`
- Universe: 20 assets from `yahoo`
- Date range: 2020-01-01 to 2025-12-31
- Holding period: 5 trading days
- Rebalance: every 5 trading days
- Long/short quantile: 20%

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

| Split | IC Mean | Sharpe | Max Drawdown | Avg Turnover | Total Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 0.0209 | 0.36 | -25.25% | 1.65 | 27.18% |
| Test | -0.0079 | -0.44 | -27.07% | 1.58 | -19.72% |
| Full | 0.0123 | 0.14 | -27.07% | 1.63 | 2.10% |

## Baseline Comparison

| Strategy | Test IC | Test Sharpe | Test Max Drawdown | Test Turnover | Test Total Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| agent_signal | -0.0079 | -0.44 | -27.07% | 1.58 | -19.72% |
| momentum_20d_only | -0.0437 | -0.61 | -37.59% | 1.65 | -29.47% |
| low_volatility_only | -0.0288 | -1.33 | -58.39% | 0.91 | -54.19% |
| reversal_5d_only | 0.0613 | 0.66 | -26.71% | 3.26 | 28.19% |
| random_cross_section | -0.0001 | -0.54 | -29.51% | 3.25 | -18.46% |

## Walk-Forward Validation

| Window | Train Through | Test Range | Obs | IC Mean | Sharpe | Hit Rate | Total Return |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| wf_01 | 2022-07-05 | 2022-07-12 to 2023-08-29 | 58 | 0.0041 | 1.18 | 50.00% | 35.52% |
| wf_02 | 2023-08-29 | 2023-09-06 to 2024-10-23 | 58 | 0.0045 | -0.39 | 46.55% | -12.53% |
| wf_03 | 2024-10-23 | 2024-10-30 to 2025-12-19 | 58 | -0.0009 | -0.21 | 48.28% | -8.63% |

| Strategy | Windows | Mean Test IC | Mean Sharpe | Positive IC Windows | Median Total Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| agent_signal | 3 | 0.0026 | 0.19 | 66.67% | -8.63% |
| momentum_20d_only | 3 | -0.0183 | 0.02 | 33.33% | 16.61% |
| low_volatility_only | 3 | -0.0387 | -1.54 | 0.00% | -45.68% |
| reversal_5d_only | 3 | 0.0206 | -0.31 | 66.67% | -1.14% |
| random_cross_section | 3 | 0.0032 | -0.80 | 66.67% | -13.78% |

## Interpretation

The signal is not supported out-of-sample in this run. Treat it as rejected until a more robust variant improves IC stability without increasing overfit risk.

The strongest out-of-sample Sharpe is from `reversal_5d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

Factor diagnostics did not flag high pairwise redundancy among selected exposures.

Walk-forward validation is not yet stable enough for promotion: inspect the weak windows before adding factor complexity.

The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.

## Limitations

- Synthetic data is useful for deterministic validation but is not investment evidence.
- v1 uses a simple long-short ranking portfolio without sector neutralization.
- Transaction costs are modeled as proportional turnover costs only.
- No borrow constraints, liquidity caps, corporate actions, or survivorship controls are included yet.

## Next Experiments

- Run the same signal on Yahoo Finance data for a real equity universe.
- Add factor correlation and redundancy analysis before combining signals.
- Stress-test promising factors with neutralization and liquidity constraints.
- Compare this factor against pure momentum, pure low volatility, and reversal baselines.
