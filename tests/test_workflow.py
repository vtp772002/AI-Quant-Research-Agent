from dataclasses import FrozenInstanceError
from pathlib import Path

import pandas as pd
import pytest

from quant_research_agent.agents.evaluator_agent import run_research_workflow
from quant_research_agent.agents.report_agent import ReportAgent, write_experiment_row
from quant_research_agent.config import parse_config


def _raw_config() -> dict[str, object]:
    return {
        "data": {
            "source": "synthetic",
            "universe": ["AAA", "BBB"],
            "start": "2020-01-01",
            "end": "2020-12-31",
        },
        "experiment": {
            "name": "config_test",
            "train_fraction": 0.7,
            "signal": {
                "positive_factors": ["momentum_20d"],
                "negative_factors": [],
            },
            "backtest": {
                "holding_period": 5,
                "rebalance_days": 5,
                "quantile": 0.2,
            },
            "validation": {
                "walk_forward": {
                    "window_count": 0,
                    "min_train_fraction": 0.4,
                }
            },
            "baselines": [],
        },
        "report": {},
    }


def test_parse_config_supports_immutable_research_validity():
    raw = _raw_config()
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        "holdout_fraction": 0.15,
        "fdr_alpha": 0.10,
        "min_holdout_sharpe": 0.25,
        "min_holdout_ic": 0.01,
        "require_positive_return": False,
        "require_baseline_outperformance": False,
        "require_walk_forward_stability": False,
        "require_data_readiness": False,
    }

    validity = parse_config(raw).experiment.validation.research_validity

    assert validity.enabled is True
    assert validity.holdout_fraction == 0.15
    assert validity.fdr_alpha == 0.10
    assert validity.min_holdout_sharpe == 0.25
    assert validity.min_holdout_ic == 0.01
    assert validity.require_positive_return is False
    assert validity.require_baseline_outperformance is False
    assert validity.require_walk_forward_stability is False
    assert validity.require_data_readiness is False
    with pytest.raises(FrozenInstanceError):
        validity.enabled = False


def test_parse_config_defaults_research_validity_for_compatibility():
    raw = _raw_config()
    raw["experiment"]["train_fraction"] = 0.9

    validity = parse_config(raw).experiment.validation.research_validity

    assert validity.enabled is False
    assert validity.holdout_fraction == 0.15
    assert validity.fdr_alpha == 0.10
    assert validity.min_holdout_sharpe == 0.0
    assert validity.min_holdout_ic == 0.0
    assert validity.require_positive_return is True
    assert validity.require_baseline_outperformance is True
    assert validity.require_walk_forward_stability is True
    assert validity.require_data_readiness is True


@pytest.mark.parametrize("holdout_fraction", [0.01, 0.45])
def test_parse_config_rejects_invalid_research_validity_holdout(holdout_fraction: float):
    raw = _raw_config()
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        "holdout_fraction": holdout_fraction,
    }

    with pytest.raises(ValueError) as exc_info:
        parse_config(raw)

    assert str(exc_info.value) == (
        "experiment.validation.research_validity.holdout_fraction "
        "must be between 0.05 and 0.40"
    )


@pytest.mark.parametrize("fdr_alpha", [0.0, 0.30])
def test_parse_config_rejects_invalid_research_validity_fdr(fdr_alpha: float):
    raw = _raw_config()
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        "fdr_alpha": fdr_alpha,
    }

    with pytest.raises(ValueError) as exc_info:
        parse_config(raw)

    assert str(exc_info.value) == (
        "experiment.validation.research_validity.fdr_alpha "
        "must be greater than 0 and at most 0.25"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_holdout_sharpe", float("inf")),
        ("min_holdout_sharpe", float("-inf")),
        ("min_holdout_ic", float("nan")),
    ],
)
def test_parse_config_rejects_non_finite_research_validity_thresholds(field: str, value: float):
    raw = _raw_config()
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        field: value,
    }

    with pytest.raises(ValueError) as exc_info:
        parse_config(raw)

    assert str(exc_info.value) == f"experiment.validation.research_validity.{field} must be finite"


def test_parse_config_preserves_validation_observations_when_research_validity_is_enabled():
    raw = _raw_config()
    raw["experiment"]["train_fraction"] = 0.8
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        "holdout_fraction": 0.15,
    }

    with pytest.raises(ValueError) as exc_info:
        parse_config(raw)

    assert str(exc_info.value) == (
        "experiment.train_fraction plus research_validity.holdout_fraction "
        "must be at most 0.90"
    )


def test_research_workflow_produces_metrics_and_report(tmp_path: Path):
    locate_path = tmp_path / "locates.csv"
    _write_locate_history(
        path=locate_path,
        symbols=["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
        start="2020-01-01",
        end="2022-12-31",
    )
    config = parse_config(
        {
            "data": {
                "source": "synthetic",
                "universe": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
                "start": "2020-01-01",
                "end": "2022-12-31",
                "seed": 11,
                "point_in_time_universe": False,
                "survivorship_bias_free": False,
                "corporate_actions_adjusted": False,
                "sectors": {
                    "AAA": "technology",
                    "BBB": "technology",
                    "CCC": "consumer",
                    "DDD": "consumer",
                    "EEE": "industrials",
                    "FFF": "industrials",
                    "GGG": "healthcare",
                    "HHH": "healthcare",
                },
            },
            "experiment": {
                "name": "test_signal",
                "train_fraction": 0.7,
                "signal": {
                    "positive_factors": ["momentum_20d"],
                    "negative_factors": ["volatility_20d"],
                },
                "backtest": {
                    "holding_period": 5,
                    "rebalance_days": 5,
                    "quantile": 0.25,
                    "transaction_cost_bps": 1.0,
                    "spread_cost_bps": 2.0,
                    "market_impact_coefficient": 0.10,
                    "portfolio_notional": 5_000_000,
                },
                "validation": {
                    "walk_forward": {
                        "window_count": 3,
                        "min_train_fraction": 0.4,
                    }
                },
                "stress_tests": {
                    "neutralization": {
                        "enabled": True,
                        "group_by": "sector",
                    },
                    "liquidity": {
                        "enabled": True,
                        "min_dollar_volume_rank": 0.2,
                    },
                },
                "shorting": {
                    "borrow_fee_bps": 100.0,
                    "shortable_symbols": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
                    "locate_history_path": str(locate_path),
                },
                "robustness": {
                    "bootstrap_iterations": 50,
                    "bootstrap_seed": 123,
                    "holding_periods": [3, 5],
                    "quantiles": [0.2, 0.25],
                    "cost_multipliers": [0.5, 1.0, 2.0],
                },
                "capacity": {
                    "notionals": [1_000_000, 5_000_000, 20_000_000],
                    "max_trade_participation": 0.05,
                    "max_position_weight": 0.35,
                },
                "baselines": [
                    {
                        "name": "momentum_20d_only",
                        "positive_factors": ["momentum_20d"],
                        "negative_factors": [],
                    },
                    {
                        "name": "reversal_20d_only",
                        "positive_factors": ["reversal_20d"],
                        "negative_factors": [],
                    },
                    {
                        "name": "random_cross_section",
                        "positive_factors": [],
                        "negative_factors": [],
                    },
                ],
            },
            "report": {
                "output_path": str(tmp_path / "report.md"),
                "experiments_path": str(tmp_path / "experiments.csv"),
            },
        }
    )

    result = run_research_workflow(config)
    report_path = ReportAgent().write_markdown_report(result, config)
    experiments_path = write_experiment_row(result, config)

    assert result.backtest.metrics["test"]["observations"] > 0
    assert result.data_integrity.source == "synthetic"
    assert result.data_integrity.row_count == len(result.market_data)
    assert result.data_integrity.warnings
    assert "sharpe" in result.backtest.metrics["full"]
    assert result.backtest.metrics["test"]["average_total_cost"] > 0
    assert result.backtest.metrics["test"]["average_spread_cost"] > 0
    assert result.backtest.metrics["test"]["average_impact_cost"] > 0
    assert result.backtest.metrics["test"]["average_borrow_cost"] > 0
    assert result.borrow_availability is not None
    assert result.borrow_availability.summary.unavailable_rows > 0
    assert result.borrow_availability.summary.hard_to_borrow_rows > 0
    assert result.backtest.metrics["test"]["max_trade_participation"] > 0
    assert result.backtest.costs["total_cost"].gt(0).any()
    assert result.backtest.positions[result.backtest.positions < 0].dropna(axis=1, how="all").columns.isin(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]).all()
    negative_positions = result.backtest.positions.stack()
    negative_positions = negative_positions[negative_positions < 0]
    for index in negative_positions.index:
        assert bool(result.borrow_availability.shortable.loc[index[0], index[1]])
    assert result.robustness.bootstrap is not None
    assert result.robustness.bootstrap.iterations == 50
    assert len(result.robustness.parameter_sensitivity) == 4
    assert len(result.robustness.cost_sensitivity) == 3
    assert result.capacity.concentration.max_single_name_weight > 0
    assert result.capacity.concentration.average_effective_positions > 0
    assert len(result.capacity.capacity_curve) == 3
    assert result.capacity.capacity_curve[-1].max_trade_participation >= result.capacity.capacity_curve[0].max_trade_participation
    assert any(item.participation_breach_count > 0 for item in result.capacity.capacity_curve)
    assert len(result.backtest.walk_forward) == 3
    assert result.backtest.walk_forward[0].metrics["observations"] > 0
    assert result.factor_diagnostics.selected_factors == ["momentum_20d", "volatility_20d", "reversal_20d"]
    assert result.factor_diagnostics.redundant_pairs
    assert result.factor_diagnostics.redundant_pairs[0].first == "momentum_20d"
    assert result.factor_diagnostics.redundant_pairs[0].second == "reversal_20d"
    assert set(result.baselines) == {"momentum_20d_only", "reversal_20d_only", "random_cross_section"}
    assert result.baselines["momentum_20d_only"].metrics["test"]["observations"] > 0
    assert len(result.baselines["momentum_20d_only"].walk_forward) == 3
    assert set(result.stress_tests) == {
        "sector_neutral_signal",
        "liquidity_top_80pct",
        "sector_neutral_liquidity_top_80pct",
    }
    assert result.stress_tests["sector_neutral_signal"].metrics["test"]["observations"] > 0
    assert len(result.stress_tests["liquidity_top_80pct"].walk_forward) == 3
    assert report_path.exists()
    report_text = report_path.read_text()
    assert "AI Quant Research Report" in report_text
    assert "Data Integrity" in report_text
    assert "Survivorship-bias-free: no" in report_text
    assert "Factor Diagnostics" in report_text
    assert "momentum_20d | reversal_20d" in report_text
    assert "Baseline Comparison" in report_text
    assert "Execution Costs" in report_text
    assert "Borrow Availability" in report_text
    assert "Hard-to-borrow rows" in report_text
    assert "Capacity Diagnostics" in report_text
    assert "Capacity curve" in report_text
    assert "Robustness Diagnostics" in report_text
    assert "Avg borrow cost" in report_text
    assert "Stress Tests" in report_text
    assert "sector_neutral_signal" in report_text
    assert "liquidity_top_80pct" in report_text
    assert "Walk-Forward Validation" in report_text
    assert "wf_01" in report_text
    assert "momentum_20d_only" in report_text
    assert experiments_path.exists()
    experiment_rows = pd.read_csv(experiments_path)
    assert set(experiment_rows["strategy"]) == {
        "agent_signal",
        "momentum_20d_only",
        "reversal_20d_only",
        "random_cross_section",
        "sector_neutral_signal",
        "liquidity_top_80pct",
        "sector_neutral_liquidity_top_80pct",
    }
    assert {"full_sample", "wf_01", "wf_02", "wf_03"}.issubset(set(experiment_rows["window"]))
    assert "test_average_total_cost" in experiment_rows.columns
    assert "test_average_borrow_cost" in experiment_rows.columns
    assert "locate_history" in experiment_rows.columns
    assert experiment_rows["locate_history"].str.contains("locates.csv").any()
    assert experiment_rows["test_average_total_cost"].gt(0).any()
    assert experiment_rows["test_average_borrow_cost"].gt(0).any()
    assert len(experiment_rows) == 28


def _write_locate_history(path: Path, symbols: list[str], start: str, end: str) -> None:
    dates = pd.bdate_range(start=start, end=end)
    rows = ["date,symbol,shortable,borrow_fee_bps,available_quantity"]
    for date in dates:
        for symbol in symbols:
            shortable = symbol not in {"GGG", "HHH"}
            if symbol == "FFF" and date.month in {6, 7}:
                shortable = False
            fee = 850.0 if symbol == "EEE" else 125.0
            quantity = 0 if not shortable else 1_000_000
            rows.append(f"{date.date().isoformat()},{symbol},{str(shortable).lower()},{fee},{quantity}")
    path.write_text("\n".join(rows), encoding="utf-8")
