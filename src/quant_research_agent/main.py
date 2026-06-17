from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_research_agent.agents.evaluator_agent import run_research_workflow
from quant_research_agent.agents.report_agent import ReportAgent, write_experiment_row
from quant_research_agent.config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an AI quant research workflow.")
    parser.add_argument("--config", default="configs/base.yaml", help="Path to YAML config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable metrics.")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    result = run_research_workflow(config)
    report_path = ReportAgent().write_markdown_report(result, config)
    experiments_path = write_experiment_row(result, config)

    payload = {
        "experiment": config.experiment.name,
        "report_path": str(report_path),
        "experiments_path": str(experiments_path),
        "data_integrity": _data_integrity_payload(result),
        "metrics": result.backtest.metrics,
        "baselines": {
            name: backtest.metrics for name, backtest in result.baselines.items()
        },
        "stress_tests": {
            name: backtest.metrics for name, backtest in result.stress_tests.items()
        },
        "walk_forward": {
            "agent_signal": _walk_forward_payload(result.backtest),
            **{
                name: _walk_forward_payload(backtest)
                for name, backtest in result.baselines.items()
            },
            **{
                name: _walk_forward_payload(backtest)
                for name, backtest in result.stress_tests.items()
            },
        },
        "factor_diagnostics": _factor_diagnostics_payload(result),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        test = result.backtest.metrics["test"]
        print(f"Experiment: {config.experiment.name}")
        print(f"Report: {report_path}")
        print(f"Results: {experiments_path}")
        print(
            "Test metrics: "
            f"IC={test['ic_mean']:.4f}, Sharpe={test['sharpe']:.2f}, "
            f"MaxDD={test['max_drawdown']:.2%}, Turnover={test['average_turnover']:.2f}"
        )
    return 0


def _walk_forward_payload(backtest) -> list[dict[str, object]]:
    return [
        {
            "window": window.name,
            "train_start": window.train_start.date().isoformat(),
            "train_end": window.train_end.date().isoformat(),
            "test_start": window.test_start.date().isoformat(),
            "test_end": window.test_end.date().isoformat(),
            "metrics": window.metrics,
        }
        for window in backtest.walk_forward
    ]


def _factor_diagnostics_payload(result) -> dict[str, object]:
    diagnostics = result.factor_diagnostics
    return {
        "selected_factors": diagnostics.selected_factors,
        "correlation_threshold": diagnostics.correlation_threshold,
        "coverage": [
            {
                "factor": item.name,
                "observations": item.observations,
                "coverage": item.coverage,
                "missing_rate": item.missing_rate,
            }
            for item in diagnostics.coverage
        ],
        "redundant_pairs": [
            {
                "first": pair.first,
                "second": pair.second,
                "correlation": pair.correlation,
            }
            for pair in diagnostics.redundant_pairs
        ],
    }


def _data_integrity_payload(result) -> dict[str, object]:
    report = result.data_integrity
    return {
        "source": report.source,
        "requested_symbols": report.requested_symbols,
        "observed_symbols": report.observed_symbols,
        "start": report.start,
        "end": report.end,
        "row_count": report.row_count,
        "date_count": report.date_count,
        "duplicate_index_rows": report.duplicate_index_rows,
        "missing_symbols": report.missing_symbols,
        "point_in_time_universe": report.point_in_time_universe,
        "survivorship_bias_free": report.survivorship_bias_free,
        "corporate_actions_adjusted": report.corporate_actions_adjusted,
        "quality_by_symbol": [
            {
                "symbol": item.symbol,
                "observations": item.observations,
                "expected_observations": item.expected_observations,
                "coverage": item.coverage,
                "missing_rows": item.missing_rows,
                "zero_volume_rows": item.zero_volume_rows,
                "non_positive_price_rows": item.non_positive_price_rows,
                "stale_price_rows": item.stale_price_rows,
                "extreme_return_rows": item.extreme_return_rows,
            }
            for item in report.quality_by_symbol
        ],
        "warnings": report.warnings,
    }


if __name__ == "__main__":
    raise SystemExit(main())
