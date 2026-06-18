from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class UniverseProviderConfig:
    kind: str = "static"
    path: Path | None = None


@dataclass(frozen=True)
class DataSnapshotConfig:
    path: Path | None = None
    manifest_path: Path | None = None
    require_manifest_hash: bool = True


@dataclass(frozen=True)
class DataConfig:
    source: str
    universe: list[str]
    start: str
    end: str
    seed: int = 42
    universe_provider: UniverseProviderConfig = field(default_factory=UniverseProviderConfig)
    snapshot: DataSnapshotConfig = field(default_factory=DataSnapshotConfig)
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
class ResearchValidityConfig:
    enabled: bool = False
    holdout_fraction: float = 0.15
    fdr_alpha: float = 0.10
    min_holdout_sharpe: float = 0.0
    min_holdout_ic: float = 0.0
    require_positive_return: bool = True
    require_baseline_outperformance: bool = True
    require_walk_forward_stability: bool = True
    require_data_readiness: bool = True


@dataclass(frozen=True)
class ValidationConfig:
    walk_forward: WalkForwardConfig
    research_validity: ResearchValidityConfig


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
class ShortingConfig:
    borrow_fee_bps: float = 0.0
    shortable_symbols: list[str] | None = None
    locate_history_path: Path | None = None


@dataclass(frozen=True)
class RobustnessConfig:
    bootstrap_iterations: int = 0
    bootstrap_seed: int = 123
    holding_periods: list[int] = field(default_factory=list)
    quantiles: list[float] = field(default_factory=list)
    cost_multipliers: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class CapacityConfig:
    notionals: list[float] = field(default_factory=list)
    max_trade_participation: float = 0.10
    max_position_weight: float = 0.10


@dataclass(frozen=True)
class ExperimentFamilyConfig:
    family_id: str | None = None
    hypothesis_id: str | None = None
    candidate_id: str | None = None
    selection_policy: str | None = None


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    family: ExperimentFamilyConfig
    train_fraction: float
    signal: SignalConfig
    backtest: BacktestConfig
    baselines: list[BaselineConfig]
    validation: ValidationConfig
    stress_tests: StressTestConfig
    shorting: ShortingConfig
    robustness: RobustnessConfig
    capacity: CapacityConfig


@dataclass(frozen=True)
class ReportConfig:
    output_path: Path
    experiments_path: Path
    registry_path: Path


@dataclass(frozen=True)
class AppConfig:
    data: DataConfig
    experiment: ExperimentConfig
    report: ReportConfig


ALLOWED_SELECTION_POLICIES = frozenset(
    {
        "pre_registered",
        "exploratory",
        "generated",
        "manual_selection",
    }
)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text()) or {}
    return parse_config(raw, base_dir=config_path.parent)


def parse_config(raw: dict[str, Any], base_dir: str | Path | None = None) -> AppConfig:
    data = raw["data"]
    experiment = raw["experiment"]
    family = experiment.get("family", {}) or {}
    signal = experiment["signal"]
    backtest = experiment["backtest"]
    validation = experiment.get("validation", {})
    walk_forward = validation.get("walk_forward", {}) or {}
    research_validity = validation.get("research_validity", {}) or {}
    stress_tests = experiment.get("stress_tests", {}) or {}
    shorting = experiment.get("shorting", {}) or {}
    robustness = experiment.get("robustness", {}) or {}
    capacity = experiment.get("capacity", {}) or {}
    neutralization = stress_tests.get("neutralization", {}) or {}
    liquidity = stress_tests.get("liquidity", {}) or {}
    report = raw["report"]
    base_path = Path(base_dir) if base_dir is not None else Path.cwd()

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

    research_validity_enabled = _parse_research_validity_bool(
        research_validity.get("enabled", False),
        "enabled",
    )
    holdout_fraction = _parse_research_validity_float(
        research_validity.get("holdout_fraction", 0.15),
        "holdout_fraction",
    )
    if not 0.05 <= holdout_fraction <= 0.40:
        raise ValueError(
            "experiment.validation.research_validity.holdout_fraction must be between 0.05 and 0.40"
        )

    fdr_alpha = _parse_research_validity_float(
        research_validity.get("fdr_alpha", 0.10),
        "fdr_alpha",
    )
    if not 0.0 < fdr_alpha <= 0.25:
        raise ValueError(
            "experiment.validation.research_validity.fdr_alpha must be greater than 0 and at most 0.25"
        )

    min_holdout_sharpe = _parse_research_validity_float(
        research_validity.get("min_holdout_sharpe", 0.0),
        "min_holdout_sharpe",
    )
    if not isfinite(min_holdout_sharpe):
        raise ValueError("experiment.validation.research_validity.min_holdout_sharpe must be finite")

    min_holdout_ic = _parse_research_validity_float(
        research_validity.get("min_holdout_ic", 0.0),
        "min_holdout_ic",
    )
    if not isfinite(min_holdout_ic):
        raise ValueError("experiment.validation.research_validity.min_holdout_ic must be finite")

    if research_validity_enabled and train_fraction + holdout_fraction > 0.90:
        raise ValueError(
            "experiment.train_fraction plus research_validity.holdout_fraction must be at most 0.90"
        )

    require_positive_return = _parse_research_validity_bool(
        research_validity.get("require_positive_return", True),
        "require_positive_return",
    )
    require_baseline_outperformance = _parse_research_validity_bool(
        research_validity.get("require_baseline_outperformance", True),
        "require_baseline_outperformance",
    )
    require_walk_forward_stability = _parse_research_validity_bool(
        research_validity.get("require_walk_forward_stability", True),
        "require_walk_forward_stability",
    )
    require_data_readiness = _parse_research_validity_bool(
        research_validity.get("require_data_readiness", True),
        "require_data_readiness",
    )

    neutralization_group_by = str(neutralization.get("group_by", "sector"))
    if neutralization_group_by != "sector":
        raise ValueError("experiment.stress_tests.neutralization.group_by must be 'sector'")

    min_dollar_volume_rank = float(liquidity.get("min_dollar_volume_rank", 0.0))
    if not 0.0 <= min_dollar_volume_rank < 1.0:
        raise ValueError("experiment.stress_tests.liquidity.min_dollar_volume_rank must be between 0 and 1")

    borrow_fee_bps = float(shorting.get("borrow_fee_bps", 0.0))
    if borrow_fee_bps < 0.0:
        raise ValueError("experiment.shorting.borrow_fee_bps must be non-negative")

    shortable_symbols = shorting.get("shortable_symbols")
    parsed_shortable_symbols = None
    if shortable_symbols is not None:
        parsed_shortable_symbols = [str(symbol).upper() for symbol in shortable_symbols]
        configured_universe = {str(symbol).upper() for symbol in data.get("universe", [])}
        unknown_shortable = set(parsed_shortable_symbols) - configured_universe if configured_universe else set()
        if unknown_shortable:
            raise ValueError(f"experiment.shorting.shortable_symbols contains unknown symbols: {sorted(unknown_shortable)}")
    locate_history_path = _resolve_optional_path(shorting.get("locate_history_path"), base_path)

    universe_provider = data.get("universe_provider", {}) or {}
    universe_provider_kind = str(universe_provider.get("kind", "static"))
    universe_provider_path = universe_provider.get("path")
    parsed_universe_provider_path = None
    if universe_provider_path is not None:
        parsed_universe_provider_path = Path(str(universe_provider_path))
        if not parsed_universe_provider_path.is_absolute():
            parsed_universe_provider_path = base_path / parsed_universe_provider_path
    if universe_provider_kind == "static" and not data.get("universe"):
        raise ValueError("data.universe is required when data.universe_provider.kind is static")

    snapshot = data.get("snapshot", {}) or {}
    snapshot_path = _resolve_optional_path(snapshot.get("path"), base_path)
    snapshot_manifest_path = _resolve_optional_path(snapshot.get("manifest_path"), base_path)
    source = str(data.get("source", "synthetic"))
    if source.lower() in {"csv_snapshot", "vendor_snapshot"} and snapshot_path is None:
        raise ValueError(f"data.snapshot.path is required when data.source={source}")

    bootstrap_iterations = int(robustness.get("bootstrap_iterations", 0))
    if bootstrap_iterations < 0:
        raise ValueError("experiment.robustness.bootstrap_iterations must be non-negative")

    holding_periods = [int(value) for value in robustness.get("holding_periods", [])]
    if any(value <= 0 for value in holding_periods):
        raise ValueError("experiment.robustness.holding_periods must contain positive integers")

    robustness_quantiles = [float(value) for value in robustness.get("quantiles", [])]
    if any(value <= 0.0 or value >= 0.5 for value in robustness_quantiles):
        raise ValueError("experiment.robustness.quantiles must be between 0 and 0.5")

    cost_multipliers = [float(value) for value in robustness.get("cost_multipliers", [])]
    if any(value < 0.0 for value in cost_multipliers):
        raise ValueError("experiment.robustness.cost_multipliers must be non-negative")

    capacity_notionals = [float(value) for value in capacity.get("notionals", [])]
    if any(value <= 0.0 for value in capacity_notionals):
        raise ValueError("experiment.capacity.notionals must contain positive values")

    max_trade_participation = float(capacity.get("max_trade_participation", 0.10))
    if not 0.0 < max_trade_participation <= 1.0:
        raise ValueError("experiment.capacity.max_trade_participation must be between 0 and 1")

    max_position_weight = float(capacity.get("max_position_weight", 0.10))
    if not 0.0 < max_position_weight <= 1.0:
        raise ValueError("experiment.capacity.max_position_weight must be between 0 and 1")

    sectors = data.get("sectors")
    parsed_sectors = None
    if sectors:
        parsed_sectors = {str(symbol).upper(): str(sector) for symbol, sector in sectors.items()}

    return AppConfig(
        data=DataConfig(
            source=source,
            universe=[str(symbol).upper() for symbol in data.get("universe", [])],
            start=str(data["start"]),
            end=str(data["end"]),
            seed=int(data.get("seed", 42)),
            universe_provider=UniverseProviderConfig(
                kind=universe_provider_kind,
                path=parsed_universe_provider_path,
            ),
            snapshot=DataSnapshotConfig(
                path=snapshot_path,
                manifest_path=snapshot_manifest_path,
                require_manifest_hash=bool(snapshot.get("require_manifest_hash", True)),
            ),
            sectors=parsed_sectors,
            point_in_time_universe=bool(data.get("point_in_time_universe", False)),
            survivorship_bias_free=bool(data.get("survivorship_bias_free", False)),
            corporate_actions_adjusted=bool(data.get("corporate_actions_adjusted", False)),
        ),
        experiment=ExperimentConfig(
            name=str(experiment["name"]),
            family=ExperimentFamilyConfig(
                family_id=_parse_optional_family_string(family.get("family_id"), "family_id"),
                hypothesis_id=_parse_optional_family_string(family.get("hypothesis_id"), "hypothesis_id"),
                candidate_id=_parse_optional_family_string(family.get("candidate_id"), "candidate_id"),
                selection_policy=_parse_selection_policy(family.get("selection_policy")),
            ),
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
                ),
                research_validity=ResearchValidityConfig(
                    enabled=research_validity_enabled,
                    holdout_fraction=holdout_fraction,
                    fdr_alpha=fdr_alpha,
                    min_holdout_sharpe=min_holdout_sharpe,
                    min_holdout_ic=min_holdout_ic,
                    require_positive_return=require_positive_return,
                    require_baseline_outperformance=require_baseline_outperformance,
                    require_walk_forward_stability=require_walk_forward_stability,
                    require_data_readiness=require_data_readiness,
                ),
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
            shorting=ShortingConfig(
                borrow_fee_bps=borrow_fee_bps,
                shortable_symbols=parsed_shortable_symbols,
                locate_history_path=locate_history_path,
            ),
            robustness=RobustnessConfig(
                bootstrap_iterations=bootstrap_iterations,
                bootstrap_seed=int(robustness.get("bootstrap_seed", 123)),
                holding_periods=holding_periods,
                quantiles=robustness_quantiles,
                cost_multipliers=cost_multipliers,
            ),
            capacity=CapacityConfig(
                notionals=capacity_notionals,
                max_trade_participation=max_trade_participation,
                max_position_weight=max_position_weight,
            ),
        ),
        report=ReportConfig(
            output_path=Path(report.get("output_path", "reports/sample_research_report.md")),
            experiments_path=Path(report.get("experiments_path", "results/experiments.csv")),
            registry_path=Path(report.get("registry_path", "results/experiments.sqlite")),
        ),
    )


def _parse_research_validity_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(
            f"experiment.validation.research_validity.{field_name} must be a boolean"
        )
    return value


def _parse_research_validity_float(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"experiment.validation.research_validity.{field_name} "
            "must be a number, not a boolean"
        )
    return float(value)


def _parse_optional_family_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise ValueError(f"experiment.family.{field_name} must not be blank when supplied")
    return text


def _parse_selection_policy(value: object) -> str | None:
    policy = _parse_optional_family_string(value, "selection_policy")
    if policy is None:
        return None
    if policy not in ALLOWED_SELECTION_POLICIES:
        allowed = ", ".join(sorted(ALLOWED_SELECTION_POLICIES))
        raise ValueError(f"experiment.family.selection_policy must be one of {allowed}")
    return policy


def _resolve_optional_path(value: object, base_path: Path) -> Path | None:
    if value is None:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = base_path / path
    return path
