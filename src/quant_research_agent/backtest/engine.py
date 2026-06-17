from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_research_agent.backtest.metrics import compute_metric_summary


@dataclass(frozen=True)
class WalkForwardWindow:
    name: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    metrics: dict[str, float]


@dataclass(frozen=True)
class BacktestResult:
    returns: pd.Series
    positions: pd.DataFrame
    ic_by_date: pd.Series
    turnover: pd.Series
    metrics: dict[str, dict[str, float]]
    split_date: pd.Timestamp
    walk_forward: list[WalkForwardWindow]


def run_long_short_backtest(
    market_data: pd.DataFrame,
    signal: pd.Series,
    train_fraction: float,
    holding_period: int,
    rebalance_days: int,
    quantile: float,
    transaction_cost_bps: float,
    walk_forward_windows: int = 0,
    walk_forward_min_train_fraction: float = 0.4,
) -> BacktestResult:
    close = market_data["adj_close"].unstack("symbol")
    forward_returns = close.shift(-holding_period) / close - 1.0
    forward_returns = forward_returns.stack().rename("forward_return")

    aligned = pd.concat([signal.rename("signal"), forward_returns], axis=1).dropna()
    rebalance_dates = _rebalance_dates(aligned.index.get_level_values("date").unique(), rebalance_days)
    aligned = aligned.loc[aligned.index.get_level_values("date").isin(rebalance_dates)]

    positions = _build_positions(aligned["signal"], quantile=quantile)
    raw_returns = _portfolio_forward_returns(positions, aligned["forward_return"])
    turnover = _turnover(positions)
    costs = turnover * (transaction_cost_bps / 10_000.0)
    returns = (raw_returns - costs).rename("strategy_return").dropna()

    ic_by_date = _information_coefficient(aligned)
    split_date = _split_date(returns.index, train_fraction)
    metrics = {
        "train": compute_metric_summary(
            returns=returns.loc[returns.index <= split_date],
            ic_by_date=ic_by_date.loc[ic_by_date.index <= split_date],
            turnover=turnover.loc[turnover.index <= split_date],
            holding_period=holding_period,
        ),
        "test": compute_metric_summary(
            returns=returns.loc[returns.index > split_date],
            ic_by_date=ic_by_date.loc[ic_by_date.index > split_date],
            turnover=turnover.loc[turnover.index > split_date],
            holding_period=holding_period,
        ),
        "full": compute_metric_summary(
            returns=returns,
            ic_by_date=ic_by_date,
            turnover=turnover,
            holding_period=holding_period,
        ),
    }
    walk_forward = _walk_forward_metrics(
        returns=returns,
        ic_by_date=ic_by_date,
        turnover=turnover,
        holding_period=holding_period,
        window_count=walk_forward_windows,
        min_train_fraction=walk_forward_min_train_fraction,
    )

    return BacktestResult(
        returns=returns,
        positions=positions,
        ic_by_date=ic_by_date,
        turnover=turnover,
        metrics=metrics,
        split_date=split_date,
        walk_forward=walk_forward,
    )


def _rebalance_dates(dates: pd.Index, rebalance_days: int) -> pd.Index:
    if rebalance_days <= 0:
        raise ValueError("rebalance_days must be positive")
    return pd.Index(sorted(dates))[::rebalance_days]


def _build_positions(signal: pd.Series, quantile: float) -> pd.DataFrame:
    frames = []
    for date, date_signal in signal.groupby(level="date"):
        values = date_signal.droplevel("date").dropna()
        if len(values) < 5:
            continue
        long_cutoff = values.quantile(1.0 - quantile)
        short_cutoff = values.quantile(quantile)
        longs = values[values >= long_cutoff].index
        shorts = values[values <= short_cutoff].index

        weights = pd.Series(0.0, index=values.index, name=date)
        if len(longs) > 0:
            weights.loc[longs] = 1.0 / len(longs)
        if len(shorts) > 0:
            weights.loc[shorts] = -1.0 / len(shorts)
        frames.append(weights)

    if not frames:
        raise ValueError("no rebalance dates had enough assets to build positions")
    positions = pd.DataFrame(frames)
    positions.index.name = "date"
    positions.columns.name = "symbol"
    return positions.sort_index()


def _portfolio_forward_returns(positions: pd.DataFrame, forward_returns: pd.Series) -> pd.Series:
    returns = forward_returns.unstack("symbol").reindex(index=positions.index, columns=positions.columns)
    return (positions * returns).sum(axis=1, min_count=1)


def _turnover(positions: pd.DataFrame) -> pd.Series:
    previous = positions.shift(1).fillna(0.0)
    return (positions - previous).abs().sum(axis=1).rename("turnover")


def _information_coefficient(aligned: pd.DataFrame) -> pd.Series:
    values = {}
    for date, frame in aligned.groupby(level="date"):
        if frame["signal"].nunique() < 2 or frame["forward_return"].nunique() < 2:
            values[date] = np.nan
        else:
            signal_rank = frame["signal"].rank()
            return_rank = frame["forward_return"].rank()
            values[date] = signal_rank.corr(return_rank)
    return pd.Series(values, name="ic").dropna()


def _split_date(index: pd.Index, train_fraction: float) -> pd.Timestamp:
    if len(index) < 4:
        raise ValueError("not enough backtest observations for train/test split")
    split_position = min(max(int(len(index) * train_fraction), 1), len(index) - 2)
    return pd.Timestamp(index[split_position])


def _walk_forward_metrics(
    returns: pd.Series,
    ic_by_date: pd.Series,
    turnover: pd.Series,
    holding_period: int,
    window_count: int,
    min_train_fraction: float,
) -> list[WalkForwardWindow]:
    if window_count <= 0:
        return []

    returns = returns.sort_index().dropna()
    if len(returns) < 4:
        return []

    min_train_size = min(max(int(len(returns) * min_train_fraction), 1), len(returns) - 1)
    remaining = len(returns) - min_train_size
    if remaining <= 0:
        return []

    actual_window_count = min(window_count, remaining)
    test_size = max(1, remaining // actual_window_count)
    windows: list[WalkForwardWindow] = []

    for index in range(actual_window_count):
        test_start_position = min_train_size + (index * test_size)
        test_end_position = len(returns) if index == actual_window_count - 1 else min(
            min_train_size + ((index + 1) * test_size),
            len(returns),
        )
        if test_start_position >= len(returns) or test_start_position >= test_end_position:
            continue

        train_returns = returns.iloc[:test_start_position]
        test_returns = returns.iloc[test_start_position:test_end_position]
        windows.append(
            WalkForwardWindow(
                name=f"wf_{index + 1:02d}",
                train_start=pd.Timestamp(train_returns.index[0]),
                train_end=pd.Timestamp(train_returns.index[-1]),
                test_start=pd.Timestamp(test_returns.index[0]),
                test_end=pd.Timestamp(test_returns.index[-1]),
                metrics=compute_metric_summary(
                    returns=test_returns,
                    ic_by_date=ic_by_date.reindex(test_returns.index),
                    turnover=turnover.reindex(test_returns.index),
                    holding_period=holding_period,
                ),
            )
        )

    return windows
