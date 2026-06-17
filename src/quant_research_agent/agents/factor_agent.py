from __future__ import annotations

import pandas as pd

from quant_research_agent.config import SignalConfig


class FactorAgent:
    def build_signal(self, factors: pd.DataFrame, config: SignalConfig) -> pd.Series:
        missing = set(config.positive_factors + config.negative_factors) - set(factors.columns)
        if missing:
            raise ValueError(f"unknown factors requested: {sorted(missing)}")

        positive_signal = sum(_cross_sectional_rank(factors[name]) for name in config.positive_factors)
        negative_signal = sum(_cross_sectional_rank(factors[name]) for name in config.negative_factors)
        signal = positive_signal - negative_signal
        signal.name = "signal"
        return signal.replace([float("inf"), float("-inf")], pd.NA).dropna()


def _cross_sectional_rank(values: pd.Series) -> pd.Series:
    return values.groupby(level="date").rank(pct=True)
