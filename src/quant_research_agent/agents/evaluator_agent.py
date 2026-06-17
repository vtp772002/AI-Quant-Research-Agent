from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_research_agent.agents.baseline_agent import BaselineAgent
from quant_research_agent.agents.factor_agent import FactorAgent
from quant_research_agent.agents.hypothesis_agent import Hypothesis, HypothesisAgent
from quant_research_agent.backtest.engine import BacktestResult, run_long_short_backtest
from quant_research_agent.config import AppConfig
from quant_research_agent.data.loader import MarketDataRequest, load_market_data
from quant_research_agent.factors.registry import compute_factor_library


@dataclass(frozen=True)
class ResearchRunResult:
    hypothesis: Hypothesis
    market_data: pd.DataFrame
    factors: pd.DataFrame
    signal: pd.Series
    backtest: BacktestResult
    baselines: dict[str, BacktestResult]


def run_research_workflow(config: AppConfig) -> ResearchRunResult:
    hypothesis = HypothesisAgent().propose(config.experiment)
    market_data = load_market_data(
        MarketDataRequest(
            source=config.data.source,
            universe=config.data.universe,
            start=config.data.start,
            end=config.data.end,
            seed=config.data.seed,
        )
    )
    factors = compute_factor_library(market_data)
    signal = FactorAgent().build_signal(factors, config.experiment.signal)
    backtest = run_long_short_backtest(
        market_data=market_data,
        signal=signal,
        train_fraction=config.experiment.train_fraction,
        holding_period=config.experiment.backtest.holding_period,
        rebalance_days=config.experiment.backtest.rebalance_days,
        quantile=config.experiment.backtest.quantile,
        transaction_cost_bps=config.experiment.backtest.transaction_cost_bps,
    )
    baselines = BaselineAgent().evaluate_baselines(
        market_data=market_data,
        factors=factors,
        config=config,
        reference_index=signal.index,
    )
    return ResearchRunResult(
        hypothesis=hypothesis,
        market_data=market_data,
        factors=factors,
        signal=signal,
        backtest=backtest,
        baselines=baselines,
    )
