from __future__ import annotations

from math import ceil

import numpy as np
import pandas as pd
import pytest

from quant_research_agent.agents.robustness import compute_robustness_diagnostics
from quant_research_agent.backtest.engine import run_long_short_backtest
from quant_research_agent.config import parse_config


def _deterministic_market_and_signal(
    periods: int = 25,
) -> tuple[pd.DataFrame, pd.Series]:
    dates = pd.bdate_range("2024-01-02", periods=periods, name="date")
    symbols = pd.Index(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"], name="symbol")
    symbol_loadings = {
        "AAA": -1.5,
        "BBB": -1.0,
        "CCC": -0.4,
        "DDD": 0.4,
        "EEE": 1.0,
        "FFF": 1.5,
    }

    prices: dict[str, list[float]] = {symbol: [100.0] for symbol in symbols}
    for position in range(1, len(dates)):
        cycle = ((position % 5) - 2) * 0.0007
        for symbol in symbols:
            loading = symbol_loadings[symbol]
            daily_return = (loading * 0.0015) + (cycle * np.sign(loading))
            prices[symbol].append(prices[symbol][-1] * (1.0 + daily_return))

    index = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    market_data = pd.DataFrame(
        {
            "adj_close": [
                prices[symbol][date_position]
                for date_position in range(len(dates))
                for symbol in symbols
            ],
            "volume": 1_000_000.0,
        },
        index=index,
    )
    signal = pd.Series(
        [symbol_loadings[symbol] for _ in dates for symbol in symbols],
        index=index,
        name="signal",
    )
    return market_data, signal


def _run_backtest(
    market_data: pd.DataFrame,
    signal: pd.Series,
    *,
    holdout_fraction: float = 0.2,
    walk_forward_windows: int = 0,
):
    return run_long_short_backtest(
        market_data=market_data,
        signal=signal,
        train_fraction=0.5,
        holdout_fraction=holdout_fraction,
        holding_period=1,
        rebalance_days=1,
        quantile=0.25,
        transaction_cost_bps=0.0,
        walk_forward_windows=walk_forward_windows,
        walk_forward_min_train_fraction=0.4,
    )


def _change_only_holdout_realized_outcomes(
    market_data: pd.DataFrame,
    holdout_start: pd.Timestamp,
) -> pd.DataFrame:
    changed = market_data.copy()
    dates = pd.Index(
        changed.index.get_level_values("date").unique()
    ).sort_values()
    future_dates = dates[dates > holdout_start]
    for step, date in enumerate(future_dates, start=1):
        changed.loc[(date, ["EEE", "FFF"]), "adj_close"] *= 1.03**step
        changed.loc[(date, ["AAA", "BBB"]), "adj_close"] *= 0.97**step
    return changed


def test_backtest_reserves_disjoint_holdout_without_changing_validation_metrics():
    market_data, signal = _deterministic_market_and_signal()
    holdout_fraction = 0.2

    original = _run_backtest(
        market_data,
        signal,
        holdout_fraction=holdout_fraction,
    )
    changed_market_data = _change_only_holdout_realized_outcomes(
        market_data,
        original.holdout_start,
    )
    rerun = _run_backtest(
        changed_market_data,
        signal,
        holdout_fraction=holdout_fraction,
    )

    train_dates = original.returns.index[original.returns.index <= original.split_date]
    validation_dates = original.returns.index[
        (original.returns.index >= original.validation_start)
        & (original.returns.index < original.holdout_start)
    ]
    holdout_dates = original.returns.index[
        original.returns.index >= original.holdout_start
    ]

    assert train_dates.max() < validation_dates.min()
    assert validation_dates.max() < holdout_dates.min()
    assert original.split_date == train_dates.max()
    assert original.validation_start == validation_dates.min()
    assert original.holdout_start == holdout_dates.min()
    assert original.metrics["validation"] == original.metrics["test"]
    assert original.metrics["validation"] is not original.metrics["test"]
    assert original.metrics["holdout"]["observations"] == ceil(
        len(original.returns) * holdout_fraction
    )
    assert original.metrics["train"] == rerun.metrics["train"]
    assert original.metrics["validation"] == rerun.metrics["validation"]
    assert original.metrics["holdout"] != rerun.metrics["holdout"]


def test_walk_forward_windows_end_before_holdout():
    market_data, signal = _deterministic_market_and_signal()

    result = _run_backtest(
        market_data,
        signal,
        holdout_fraction=0.2,
        walk_forward_windows=4,
    )

    assert result.walk_forward
    assert all(window.test_end < result.holdout_start for window in result.walk_forward)


def test_bootstrap_samples_validation_without_holdout():
    market_data, signal = _deterministic_market_and_signal()
    original = _run_backtest(market_data, signal, holdout_fraction=0.2)
    changed_market_data = _change_only_holdout_realized_outcomes(
        market_data,
        original.holdout_start,
    )
    changed = _run_backtest(changed_market_data, signal, holdout_fraction=0.2)
    config = parse_config(
        {
            "data": {
                "source": "synthetic",
                "universe": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
                "start": "2024-01-02",
                "end": "2024-02-05",
            },
            "experiment": {
                "name": "holdout_bootstrap",
                "train_fraction": 0.5,
                "signal": {
                    "positive_factors": ["momentum_20d"],
                    "negative_factors": [],
                },
                "backtest": {
                    "holding_period": 1,
                    "rebalance_days": 1,
                    "quantile": 0.25,
                },
                "validation": {
                    "research_validity": {
                        "enabled": True,
                        "holdout_fraction": 0.2,
                    }
                },
                "robustness": {
                    "bootstrap_iterations": 100,
                    "bootstrap_seed": 17,
                },
                "baselines": [],
            },
            "report": {},
        }
    )

    original_diagnostics = compute_robustness_diagnostics(
        market_data=market_data,
        signal=signal,
        backtest=original,
        config=config,
    )
    changed_diagnostics = compute_robustness_diagnostics(
        market_data=changed_market_data,
        signal=signal,
        backtest=changed,
        config=config,
    )

    assert original_diagnostics.bootstrap is not None
    assert original_diagnostics.bootstrap == changed_diagnostics.bootstrap


def test_disabled_holdout_preserves_train_test_compatibility():
    market_data, signal = _deterministic_market_and_signal()

    result = _run_backtest(
        market_data,
        signal,
        holdout_fraction=0.0,
        walk_forward_windows=3,
    )

    legacy_test_dates = result.returns.index[result.returns.index > result.split_date]
    assert result.validation_start == legacy_test_dates.min()
    assert result.holdout_start is None
    assert result.metrics["validation"] == result.metrics["test"]
    assert result.metrics["validation"]["observations"] == float(len(legacy_test_dates))
    assert set(result.metrics) == {"train", "validation", "test", "holdout", "full"}
    assert all(value == 0.0 for value in result.metrics["holdout"].values())
    assert result.walk_forward
    assert result.walk_forward[-1].test_end == result.returns.index.max()


def test_enabled_holdout_rejects_too_few_observations():
    market_data, signal = _deterministic_market_and_signal(periods=4)

    with pytest.raises(
        ValueError,
        match="^not enough backtest observations for train, validation, and holdout$",
    ):
        _run_backtest(market_data, signal, holdout_fraction=0.4)


def test_enabled_holdout_allows_one_observation_per_partition():
    market_data, signal = _deterministic_market_and_signal(periods=4)

    result = _run_backtest(market_data, signal, holdout_fraction=0.2)

    assert result.metrics["train"]["observations"] == 1.0
    assert result.metrics["validation"]["observations"] == 1.0
    assert result.metrics["holdout"]["observations"] == 1.0
