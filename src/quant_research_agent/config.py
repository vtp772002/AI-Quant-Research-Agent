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
class ExperimentConfig:
    name: str
    train_fraction: float
    signal: SignalConfig
    backtest: BacktestConfig
    baselines: list[BaselineConfig]
    validation: ValidationConfig


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
    report = raw["report"]

    train_fraction = float(experiment.get("train_fraction", 0.7))
    if not 0.1 <= train_fraction <= 0.9:
        raise ValueError("experiment.train_fraction must be between 0.1 and 0.9")

    quantile = float(backtest.get("quantile", 0.2))
    if not 0.0 < quantile < 0.5:
        raise ValueError("experiment.backtest.quantile must be between 0 and 0.5")

    walk_forward_window_count = int(walk_forward.get("window_count", 0))
    if walk_forward_window_count < 0:
        raise ValueError("experiment.validation.walk_forward.window_count must be non-negative")

    walk_forward_min_train_fraction = float(walk_forward.get("min_train_fraction", 0.4))
    if not 0.1 <= walk_forward_min_train_fraction <= 0.9:
        raise ValueError("experiment.validation.walk_forward.min_train_fraction must be between 0.1 and 0.9")

    return AppConfig(
        data=DataConfig(
            source=str(data.get("source", "synthetic")),
            universe=[str(symbol).upper() for symbol in data["universe"]],
            start=str(data["start"]),
            end=str(data["end"]),
            seed=int(data.get("seed", 42)),
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
                transaction_cost_bps=float(backtest.get("transaction_cost_bps", 0.0)),
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
        ),
        report=ReportConfig(
            output_path=Path(report.get("output_path", "reports/sample_research_report.md")),
            experiments_path=Path(report.get("experiments_path", "results/experiments.csv")),
        ),
    )
