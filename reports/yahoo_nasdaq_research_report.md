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

## Interpretation

The signal is not supported out-of-sample in this run. Treat it as rejected until a more robust variant improves IC stability without increasing overfit risk.

The strongest out-of-sample Sharpe is from `reversal_5d_only`, not the agent signal. Treat this as a useful rejection/iteration signal: inspect which factor exposure is carrying the result before adding model complexity.

The train/test split is chronological. Test-period results are the primary evidence because they are less exposed to factor selection bias.

## Limitations

- Synthetic data is useful for deterministic validation but is not investment evidence.
- v1 uses a simple long-short ranking portfolio without sector neutralization.
- Transaction costs are modeled as proportional turnover costs only.
- No borrow constraints, liquidity caps, corporate actions, or survivorship controls are included yet.

## Next Experiments

- Run the same signal on Yahoo Finance data for a real equity universe.
- Add factor correlation and redundancy analysis before combining signals.
- Add walk-forward validation over multiple expanding windows.
- Compare this factor against pure momentum, pure low volatility, and reversal baselines.
