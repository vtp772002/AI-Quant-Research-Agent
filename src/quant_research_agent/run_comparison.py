from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import json


@dataclass(frozen=True)
class RunComparisonRow:
    rank: int
    run_id: str
    experiment: str
    generated_at: str
    source: str
    dataset_id: str | None
    config_sha256: str
    code_commit: str
    code_dirty: bool
    test_sharpe: float
    test_total_return: float
    test_ic_mean: float
    test_max_drawdown: float
    test_average_total_cost: float
    test_average_turnover: float
    observed_symbols: int
    manifest_path: str


@dataclass(frozen=True)
class RunComparison:
    run_count: int
    metric: str
    rows: list[RunComparisonRow]
    warnings: list[str]
    summary: dict[str, object]


def compare_run_manifests(path: Path, metric: str = "sharpe", limit: int | None = None) -> RunComparison:
    manifest_paths = _discover_manifests(path)
    rows = [_row_from_manifest(manifest_path) for manifest_path in manifest_paths]
    reverse = metric not in {"max_drawdown", "average_total_cost", "average_turnover"}
    sorted_rows = sorted(rows, key=lambda row: _metric_value(row, metric), reverse=reverse)
    if limit is not None:
        sorted_rows = sorted_rows[:limit]
    ranked = [
        RunComparisonRow(rank=index + 1, **{key: value for key, value in row.__dict__.items() if key != "rank"})
        for index, row in enumerate(sorted_rows)
    ]
    return RunComparison(
        run_count=len(rows),
        metric=metric,
        rows=ranked,
        warnings=_warnings(rows),
        summary=_summary(rows),
    )


def comparison_to_dict(comparison: RunComparison) -> dict[str, object]:
    return {
        "run_count": comparison.run_count,
        "metric": comparison.metric,
        "summary": comparison.summary,
        "warnings": comparison.warnings,
        "rows": [row.__dict__ for row in comparison.rows],
    }


def comparison_to_markdown(comparison: RunComparison) -> str:
    lines = [
        "# Run Comparison",
        "",
        f"- Runs discovered: `{comparison.run_count}`",
        f"- Ranking metric: `{comparison.metric}`",
        f"- Best run: `{comparison.rows[0].run_id if comparison.rows else 'none'}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in comparison.summary.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Ranked Runs",
            "",
            "| Rank | Run ID | Experiment | Source | Dataset | Sharpe | Return | IC | Max DD | Cost | Turnover |",
            "| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in comparison.rows:
        lines.append(
            "| "
            f"{row.rank} | `{row.run_id}` | {row.experiment} | {row.source} | {row.dataset_id or ''} | "
            f"{row.test_sharpe:.4f} | {row.test_total_return:.4f} | {row.test_ic_mean:.4f} | "
            f"{row.test_max_drawdown:.4f} | {row.test_average_total_cost:.6f} | {row.test_average_turnover:.4f} |"
        )
    if comparison.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in comparison.warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def _discover_manifests(path: Path) -> list[Path]:
    path = path.expanduser()
    if path.is_file():
        manifest_paths = [path]
    else:
        manifest_paths = sorted(path.glob("*/manifest.json"))
    if not manifest_paths:
        raise FileNotFoundError(f"No manifest.json files found under {path}")
    return manifest_paths


def _row_from_manifest(path: Path) -> RunComparisonRow:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    metrics = manifest["metrics"]["test"]
    data = manifest.get("data", {})
    code = manifest.get("code", {})
    observed_symbols = data.get("observed_symbols") or []
    return RunComparisonRow(
        rank=0,
        run_id=str(manifest["run_id"]),
        experiment=str(manifest["experiment"]),
        generated_at=str(manifest["generated_at"]),
        source=str(data.get("source", "unknown")),
        dataset_id=data.get("snapshot_dataset_id"),
        config_sha256=str(manifest["config"]["sha256"]),
        code_commit=str(code.get("commit", "unknown")),
        code_dirty=bool(code.get("dirty", False)),
        test_sharpe=float(metrics.get("sharpe", 0.0)),
        test_total_return=float(metrics.get("total_return", 0.0)),
        test_ic_mean=float(metrics.get("ic_mean", 0.0)),
        test_max_drawdown=float(metrics.get("max_drawdown", 0.0)),
        test_average_total_cost=float(metrics.get("average_total_cost", 0.0)),
        test_average_turnover=float(metrics.get("average_turnover", 0.0)),
        observed_symbols=len(observed_symbols),
        manifest_path=str(path),
    )


def _metric_value(row: RunComparisonRow, metric: str) -> float:
    field = f"test_{metric}"
    if not hasattr(row, field):
        allowed = [
            "sharpe",
            "total_return",
            "ic_mean",
            "max_drawdown",
            "average_total_cost",
            "average_turnover",
        ]
        raise ValueError(f"Unsupported comparison metric {metric!r}; expected one of {', '.join(allowed)}")
    return float(getattr(row, field))


def _warnings(rows: list[RunComparisonRow]) -> list[str]:
    warnings: list[str] = []
    if len({row.config_sha256 for row in rows}) > 1:
        warnings.append("Compared runs use different config hashes.")
    if len({row.code_commit for row in rows}) > 1:
        warnings.append("Compared runs use different git commits.")
    if any(row.code_dirty for row in rows):
        warnings.append("At least one compared run was generated from a dirty git worktree.")
    if len({row.source for row in rows}) > 1:
        warnings.append("Compared runs use different data sources.")
    if len({row.dataset_id for row in rows}) > 1:
        warnings.append("Compared runs use different snapshot dataset ids.")
    return warnings


def _summary(rows: list[RunComparisonRow]) -> dict[str, object]:
    return {
        "unique_experiments": len({row.experiment for row in rows}),
        "unique_configs": len({row.config_sha256 for row in rows}),
        "unique_code_commits": len({row.code_commit for row in rows}),
        "unique_sources": len({row.source for row in rows}),
        "average_test_sharpe": round(mean(row.test_sharpe for row in rows), 6),
        "average_test_return": round(mean(row.test_total_return for row in rows), 6),
        "average_test_cost": round(mean(row.test_average_total_cost for row in rows), 8),
    }
