from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DataConfig:
    source: str
    universe: list[str]
    start: str
    end: str
    seed: int = 42
    sectors: dict[str, str] | None = None
    point_in_time_universe: bool = False
    survivorship_bias_free: bool = False
    corporate_actions_adjusted: bool = False


@dataclass(frozen=True)
class SignalConfig:
    positive_factors: list[str]
    negative_factors: list[str]
    rank_method: str = "percentile"


@dataclass(frozen=True)
class BacktestConfig:
    holding_period: int
    rebalance_days: int
    quantile: float
    transaction_cost_bps: float = 0.0
    spread_cost_bps: float = 0.0
    market_impact_coefficient: float = 0.0
    portfolio_notional: float = 1_000_000.0


@dataclass(frozen=True)
class BaselineConfig:
    name: str
    positive_factors: list[str]
    negative_factors: list[str]


@dataclass(frozen=True)
class WalkForwardConfig:
    window_count: int = 0
    min_train_fraction: float = 0.4


@dataclass(frozen=True)
class ValidationConfig:
    walk_forward: WalkForwardConfig


@dataclass(frozen=True)
class NeutralizationConfig:
    enabled: bool = False
    group_by: str = "sector"


@dataclass(frozen=True)
class LiquidityStressConfig:
    enabled: bool = False
    min_dollar_volume_rank: float = 0.0


@dataclass(frozen=True)
class StressTestConfig:
    neutralization: NeutralizationConfig
    liquidity: LiquidityStressConfig


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    train_fraction: float
    signal: SignalConfig
    backtest: BacktestConfig
    baselines: list[BaselineConfig]
    validation: ValidationConfig
    stress_tests: StressTestConfig


@dataclass(frozen=True)
class ReportConfig:
    output_path: Path
    experiments_path: Path


@dataclass(frozen=True)
class AppConfig:
    data: DataConfig
    experiment: ExperimentConfig
    report: ReportConfig


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    return parse_config(raw)


def parse_config(raw: dict[str, Any]) -> AppConfig:
    data = raw["data"]
    experiment = raw["experiment"]
    signal = experiment["signal"]
    backtest = experiment["backtest"]
    validation = experiment.get("validation", {})
    walk_forward = validation.get("walk_forward", {}) or {}
    stress_tests = experiment.get("stress_tests", {}) or {}
    neutralization = stress_tests.get("neutralization", {}) or {}
    liquidity = stress_tests.get("liquidity", {}) or {}
    report = raw["report"]

    train_fraction = float(experiment.get("train_fraction", 0.7))
    if not 0.1 <= train_fraction <= 0.9:
        raise ValueError("experiment.train_fraction must be between 0.1 and 0.9")

    quantile = float(backtest.get("quantile", 0.2))
    if not 0.0 < quantile < 0.5:
        raise ValueError("experiment.backtest.quantile must be between 0 and 0.5")

    transaction_cost_bps = float(backtest.get("transaction_cost_bps", 0.0))
    if transaction_cost_bps < 0.0:
        raise ValueError("experiment.backtest.transaction_cost_bps must be non-negative")

    spread_cost_bps = float(backtest.get("spread_cost_bps", 0.0))
    if spread_cost_bps < 0.0:
        raise ValueError("experiment.backtest.spread_cost_bps must be non-negative")

    market_impact_coefficient = float(backtest.get("market_impact_coefficient", 0.0))
    if market_impact_coefficient < 0.0:
        raise ValueError("experiment.backtest.market_impact_coefficient must be non-negative")

    portfolio_notional = float(backtest.get("portfolio_notional", 1_000_000.0))
    if portfolio_notional <= 0.0:
        raise ValueError("experiment.backtest.portfolio_notional must be positive")

    walk_forward_window_count = int(walk_forward.get("window_count", 0))
    if walk_forward_window_count < 0:
        raise ValueError("experiment.validation.walk_forward.window_count must be non-negative")

    walk_forward_min_train_fraction = float(walk_forward.get("min_train_fraction", 0.4))
    if not 0.1 <= walk_forward_min_train_fraction <= 0.9:
        raise ValueError("experiment.validation.walk_forward.min_train_fraction must be between 0.1 and 0.9")

    neutralization_group_by = str(neutralization.get("group_by", "sector"))
    if neutralization_group_by != "sector":
        raise ValueError("experiment.stress_tests.neutralization.group_by must be 'sector'")

    min_dollar_volume_rank = float(liquidity.get("min_dollar_volume_rank", 0.0))
    if not 0.0 <= min_dollar_volume_rank < 1.0:
        raise ValueError("experiment.stress_tests.liquidity.min_dollar_volume_rank must be between 0 and 1")

    sectors = data.get("sectors")
    parsed_sectors = None
    if sectors:
        parsed_sectors = {str(symbol).upper(): str(sector) for symbol, sector in sectors.items()}

    return AppConfig(
        data=DataConfig(
            source=str(data.get("source", "synthetic")),
            universe=[str(symbol).upper() for symbol in data["universe"]],
            start=str(data["start"]),
            end=str(data["end"]),
            seed=int(data.get("seed", 42)),
            sectors=parsed_sectors,
            point_in_time_universe=bool(data.get("point_in_time_universe", False)),
            survivorship_bias_free=bool(data.get("survivorship_bias_free", False)),
            corporate_actions_adjusted=bool(data.get("corporate_actions_adjusted", False)),
        ),
        experiment=ExperimentConfig(
            name=str(experiment["name"]),
            train_fraction=train_fraction,
            signal=SignalConfig(
                positive_factors=[str(name) for name in signal.get("positive_factors", [])],
                negative_factors=[str(name) for name in signal.get("negative_factors", [])],
                rank_method=str(signal.get("rank_method", "percentile")),
            ),
            backtest=BacktestConfig(
                holding_period=int(backtest.get("holding_period", 5)),
                rebalance_days=int(backtest.get("rebalance_days", 5)),
                quantile=quantile,
                transaction_cost_bps=transaction_cost_bps,
                spread_cost_bps=spread_cost_bps,
                market_impact_coefficient=market_impact_coefficient,
                portfolio_notional=portfolio_notional,
            ),
            baselines=[
                BaselineConfig(
                    name=str(baseline["name"]),
                    positive_factors=[str(name) for name in baseline.get("positive_factors", [])],
                    negative_factors=[str(name) for name in baseline.get("negative_factors", [])],
                )
                for baseline in experiment.get("baselines", [])
            ],
            validation=ValidationConfig(
                walk_forward=WalkForwardConfig(
                    window_count=walk_forward_window_count,
                    min_train_fraction=walk_forward_min_train_fraction,
                )
            ),
            stress_tests=StressTestConfig(
                neutralization=NeutralizationConfig(
                    enabled=bool(neutralization.get("enabled", False)),
                    group_by=neutralization_group_by,
                ),
                liquidity=LiquidityStressConfig(
                    enabled=bool(liquidity.get("enabled", False)),
                    min_dollar_volume_rank=min_dollar_volume_rank,
                ),
            ),
        ),
        report=ReportConfig(
            output_path=Path(report.get("output_path", "reports/sample_research_report.md")),
            experiments_path=Path(report.get("experiments_path", "results/experiments.csv")),
        ),
    )
