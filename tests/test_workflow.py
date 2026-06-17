from pathlib import Path

import pandas as pd

from quant_research_agent.agents.evaluator_agent import run_research_workflow
from quant_research_agent.agents.report_agent import ReportAgent, write_experiment_row
from quant_research_agent.config import parse_config


def test_research_workflow_produces_metrics_and_report(tmp_path: Path):
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
                },
                "robustness": {
                    "bootstrap_iterations": 50,
                    "bootstrap_seed": 123,
                    "holding_periods": [3, 5],
                    "quantiles": [0.2, 0.25],
                    "cost_multipliers": [0.5, 1.0, 2.0],
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
    assert result.backtest.metrics["test"]["max_trade_participation"] > 0
    assert result.backtest.costs["total_cost"].gt(0).any()
    assert result.backtest.positions[result.backtest.positions < 0].dropna(axis=1, how="all").columns.isin(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]).all()
    assert result.robustness.bootstrap is not None
    assert result.robustness.bootstrap.iterations == 50
    assert len(result.robustness.parameter_sensitivity) == 4
    assert len(result.robustness.cost_sensitivity) == 3
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
    assert experiment_rows["test_average_total_cost"].gt(0).any()
    assert experiment_rows["test_average_borrow_cost"].gt(0).any()
    assert len(experiment_rows) == 28
