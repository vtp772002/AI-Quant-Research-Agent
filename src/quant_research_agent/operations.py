from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json

from quant_research_agent.run_comparison import (
    compare_run_manifests,
    comparison_to_dict,
    comparison_to_markdown,
)
from quant_research_agent.workflow import WorkflowRun, run_configured_workflow


@dataclass(frozen=True)
class BatchRunResult:
    status: str
    runs: list[WorkflowRun]
    failures: list[dict[str, str]]
    summary_path: Path
    comparison_markdown_path: Path | None
    comparison_json_path: Path | None


def run_research_batch(
    config_paths: list[Path],
    output_dir: Path,
    comparison_metric: str = "sharpe",
    limit: int | None = None,
) -> BatchRunResult:
    if not config_paths:
        raise ValueError("at least one config path is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    runs: list[WorkflowRun] = []
    failures: list[dict[str, str]] = []
    for config_path in config_paths:
        try:
            runs.append(run_configured_workflow(config_path))
        except Exception as exc:  # pragma: no cover - exercised through CLI/process boundaries.
            failures.append({"config_path": str(config_path), "error": str(exc)})

    summary_path = output_dir / "batch_summary.json"
    comparison_markdown_path = output_dir / "run_comparison.md" if runs else None
    comparison_json_path = output_dir / "run_comparison.json" if runs else None
    summary = {
        "status": "failed" if failures else "completed",
        "requested_configs": [str(path) for path in config_paths],
        "successful_runs": len(runs),
        "failed_runs": len(failures),
        "run_ids": [run.manifest["run_id"] for run in runs],
        "failures": failures,
        "comparison_markdown_path": str(comparison_markdown_path) if comparison_markdown_path else None,
        "comparison_json_path": str(comparison_json_path) if comparison_json_path else None,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    if runs:
        runs_root = Path(runs[0].manifest["artifacts"]["manifest_path"]).parent.parent
        comparison = compare_run_manifests(runs_root, metric=comparison_metric, limit=limit)
        assert comparison_markdown_path is not None
        assert comparison_json_path is not None
        comparison_markdown_path.write_text(comparison_to_markdown(comparison), encoding="utf-8")
        comparison_json_path.write_text(
            json.dumps(comparison_to_dict(comparison), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return BatchRunResult(
        status=str(summary["status"]),
        runs=runs,
        failures=failures,
        summary_path=summary_path,
        comparison_markdown_path=comparison_markdown_path,
        comparison_json_path=comparison_json_path,
    )


def batch_result_to_dict(result: BatchRunResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "successful_runs": len(result.runs),
        "failed_runs": len(result.failures),
        "run_ids": [run.manifest["run_id"] for run in result.runs],
        "failures": result.failures,
        "summary_path": str(result.summary_path),
        "comparison_markdown_path": str(result.comparison_markdown_path) if result.comparison_markdown_path else None,
        "comparison_json_path": str(result.comparison_json_path) if result.comparison_json_path else None,
    }
