from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_research_agent.run_comparison import (
    compare_run_manifests,
    comparison_to_dict,
    comparison_to_markdown,
)
from quant_research_agent.workflow import run_configured_workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an AI quant research workflow.")
    parser.add_argument("--config", default="configs/base.yaml", help="Path to YAML config.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable metrics.")
    parser.add_argument(
        "--compare-runs",
        help="Compare reproducibility manifests under a results/runs directory or a single manifest path.",
    )
    parser.add_argument(
        "--comparison-metric",
        default="sharpe",
        choices=[
            "sharpe",
            "total_return",
            "ic_mean",
            "max_drawdown",
            "average_total_cost",
            "average_turnover",
        ],
        help="Metric used to rank compared runs.",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of compared runs to return.")
    parser.add_argument("--output", help="Optional path for comparison output.")
    args = parser.parse_args(argv)

    if args.compare_runs:
        comparison = compare_run_manifests(
            Path(args.compare_runs),
            metric=args.comparison_metric,
            limit=args.limit,
        )
        if args.json:
            rendered = json.dumps(comparison_to_dict(comparison), indent=2, sort_keys=True)
        else:
            rendered = comparison_to_markdown(comparison)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            print(f"Comparison: {output_path}")
        else:
            print(rendered)
        return 0

    workflow = run_configured_workflow(Path(args.config))
    payload = workflow.payload
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        test = workflow.result.backtest.metrics["test"]
        print(f"Experiment: {workflow.config.experiment.name}")
        print(f"Run: {workflow.manifest['run_id']}")
        print(f"Report: {workflow.report_path}")
        print(f"Results: {workflow.experiments_path}")
        print(f"Manifest: {workflow.manifest['artifacts']['manifest_path']}")
        print(f"Registry: {workflow.config.report.registry_path}")
        print(
            "Test metrics: "
            f"IC={test['ic_mean']:.4f}, Sharpe={test['sharpe']:.2f}, "
            f"MaxDD={test['max_drawdown']:.2%}, Turnover={test['average_turnover']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
