from __future__ import annotations

import numpy as np
import pandas as pd


def factor_names() -> list[str]:
    return [
        "momentum_5d",
        "momentum_10d",
        "momentum_20d",
        "momentum_60d",
        "reversal_5d",
        "reversal_10d",
        "reversal_20d",
        "volatility_10d",
        "volatility_20d",
        "volatility_60d",
        "downside_volatility_20d",
        "volume_spike_5d",
        "volume_spike_20d",
        "dollar_volume_20d",
        "price_volume_corr_20d",
        "rsi_14",
        "moving_average_gap_20d",
        "moving_average_gap_50d",
        "return_zscore_20d",
        "drawdown_20d",
        "drawdown_60d",
        "amihud_illiquidity_20d",
    ]


def compute_factor_library(market_data: pd.DataFrame) -> pd.DataFrame:
    close = market_data["adj_close"].unstack("symbol")
    volume = market_data["volume"].unstack("symbol")
    returns = close.pct_change(fill_method=None)
    dollar_volume = close * volume

    factors: dict[str, pd.DataFrame] = {
        "momentum_5d": close.pct_change(5, fill_method=None),
        "momentum_10d": close.pct_change(10, fill_method=None),
        "momentum_20d": close.pct_change(20, fill_method=None),
        "momentum_60d": close.pct_change(60, fill_method=None),
        "volatility_10d": returns.rolling(10).std(),
        "volatility_20d": returns.rolling(20).std(),
        "volatility_60d": returns.rolling(60).std(),
        "downside_volatility_20d": returns.where(returns < 0).rolling(20).std(),
        "volume_spike_5d": volume / volume.rolling(5).mean() - 1.0,
        "volume_spike_20d": volume / volume.rolling(20).mean() - 1.0,
        "dollar_volume_20d": np.log1p(dollar_volume.rolling(20).mean()),
        "price_volume_corr_20d": returns.rolling(20).corr(volume.pct_change(fill_method=None)),
        "rsi_14": _rsi(close, 14),
        "moving_average_gap_20d": close / close.rolling(20).mean() - 1.0,
        "moving_average_gap_50d": close / close.rolling(50).mean() - 1.0,
        "return_zscore_20d": (returns - returns.rolling(20).mean()) / returns.rolling(20).std(),
        "drawdown_20d": close / close.rolling(20).max() - 1.0,
        "drawdown_60d": close / close.rolling(60).max() - 1.0,
        "amihud_illiquidity_20d": (returns.abs() / dollar_volume.replace(0, np.nan)).rolling(20).mean(),
    }
    factors["reversal_5d"] = -factors["momentum_5d"]
    factors["reversal_10d"] = -factors["momentum_10d"]
    factors["reversal_20d"] = -factors["momentum_20d"]

    stacked = []
    for name in factor_names():
        frame = factors[name].stack().rename(name)
        stacked.append(frame)

    factor_frame = pd.concat(stacked, axis=1)
    factor_frame.index.names = ["date", "symbol"]
    return factor_frame.replace([np.inf, -np.inf], np.nan).sort_index()


def _rsi(close: pd.DataFrame, window: int) -> pd.DataFrame:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + relative_strength))
