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
                },
                "validation": {
                    "walk_forward": {
                        "window_count": 3,
                        "min_train_fraction": 0.4,
                    }
                },
                "baselines": [
                    {
                        "name": "momentum_20d_only",
                        "positive_factors": ["momentum_20d"],
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
    assert "sharpe" in result.backtest.metrics["full"]
    assert len(result.backtest.walk_forward) == 3
    assert result.backtest.walk_forward[0].metrics["observations"] > 0
    assert set(result.baselines) == {"momentum_20d_only", "random_cross_section"}
    assert result.baselines["momentum_20d_only"].metrics["test"]["observations"] > 0
    assert len(result.baselines["momentum_20d_only"].walk_forward) == 3
    assert report_path.exists()
    report_text = report_path.read_text()
    assert "AI Quant Research Report" in report_text
    assert "Baseline Comparison" in report_text
    assert "Walk-Forward Validation" in report_text
    assert "wf_01" in report_text
    assert "momentum_20d_only" in report_text
    assert experiments_path.exists()
    experiment_rows = pd.read_csv(experiments_path)
    assert set(experiment_rows["strategy"]) == {
        "agent_signal",
        "momentum_20d_only",
        "random_cross_section",
    }
    assert {"full_sample", "wf_01", "wf_02", "wf_03"}.issubset(set(experiment_rows["window"]))
    assert len(experiment_rows) == 12
