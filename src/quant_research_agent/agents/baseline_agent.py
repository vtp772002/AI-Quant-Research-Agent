from __future__ import annotations

import numpy as np
import pandas as pd

from quant_research_agent.agents.factor_agent import FactorAgent
from quant_research_agent.backtest.engine import BacktestResult, run_long_short_backtest
from quant_research_agent.config import AppConfig, BaselineConfig, SignalConfig


class BaselineAgent:
    def evaluate_baselines(
        self,
        market_data: pd.DataFrame,
        factors: pd.DataFrame,
        config: AppConfig,
        reference_index: pd.Index,
    ) -> dict[str, BacktestResult]:
        baselines: dict[str, BacktestResult] = {}
        for baseline in config.experiment.baselines:
            signal = _signal_for_baseline(factors, baseline, reference_index)
            baselines[baseline.name] = run_long_short_backtest(
                market_data=market_data,
                signal=signal,
                train_fraction=config.experiment.train_fraction,
                holding_period=config.experiment.backtest.holding_period,
                rebalance_days=config.experiment.backtest.rebalance_days,
                quantile=config.experiment.backtest.quantile,
                transaction_cost_bps=config.experiment.backtest.transaction_cost_bps,
            )
        return baselines


def _signal_for_baseline(
    factors: pd.DataFrame,
    baseline: BaselineConfig,
    reference_index: pd.Index,
) -> pd.Series:
    if baseline.name == "random_cross_section":
        return _deterministic_random_signal(reference_index)
    signal = FactorAgent().build_signal(
        factors,
        SignalConfig(
            positive_factors=baseline.positive_factors,
            negative_factors=baseline.negative_factors,
        ),
    )
    return signal.reindex(reference_index).dropna()


def _deterministic_random_signal(reference_index: pd.Index) -> pd.Series:
    rng = np.random.default_rng(12345)
    signal = pd.Series(rng.normal(size=len(reference_index)), index=reference_index, name="signal")
    return signal
