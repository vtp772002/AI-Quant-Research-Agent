from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_research_agent.config import AppConfig


@dataclass(frozen=True)
class FactorCoverage:
    name: str
    observations: int
    coverage: float
    missing_rate: float


@dataclass(frozen=True)
class RedundantFactorPair:
    first: str
    second: str
    correlation: float


@dataclass(frozen=True)
class FactorDiagnostics:
    selected_factors: list[str]
    coverage: list[FactorCoverage]
    redundant_pairs: list[RedundantFactorPair]
    correlation_threshold: float


def selected_factor_names(config: AppConfig) -> list[str]:
    names: list[str] = []
    names.extend(config.experiment.signal.positive_factors)
    names.extend(config.experiment.signal.negative_factors)
    for baseline in config.experiment.baselines:
        names.extend(baseline.positive_factors)
        names.extend(baseline.negative_factors)
    return list(dict.fromkeys(names))


def compute_factor_diagnostics(
    factors: pd.DataFrame,
    selected_factors: list[str],
    correlation_threshold: float = 0.75,
) -> FactorDiagnostics:
    missing = set(selected_factors) - set(factors.columns)
    if missing:
        raise ValueError(f"unknown factors requested for diagnostics: {sorted(missing)}")

    selected = factors[selected_factors] if selected_factors else pd.DataFrame(index=factors.index)
    coverage = [
        FactorCoverage(
            name=name,
            observations=int(selected[name].notna().sum()),
            coverage=float(selected[name].notna().mean()) if len(selected) else 0.0,
            missing_rate=float(selected[name].isna().mean()) if len(selected) else 0.0,
        )
        for name in selected_factors
    ]

    redundant_pairs: list[RedundantFactorPair] = []
    if len(selected_factors) >= 2:
        correlation = selected.corr(method="spearman", min_periods=30)
        for left_index, first in enumerate(selected_factors):
            for second in selected_factors[left_index + 1 :]:
                value = correlation.loc[first, second]
                if pd.notna(value) and abs(float(value)) >= correlation_threshold:
                    redundant_pairs.append(
                        RedundantFactorPair(
                            first=first,
                            second=second,
                            correlation=float(value),
                        )
                    )

    redundant_pairs.sort(key=lambda pair: abs(pair.correlation), reverse=True)
    return FactorDiagnostics(
        selected_factors=selected_factors,
        coverage=coverage,
        redundant_pairs=redundant_pairs,
        correlation_threshold=correlation_threshold,
    )
