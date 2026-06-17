from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_research_agent.main import main
from quant_research_agent.run_comparison import (
    compare_run_manifests,
    comparison_to_dict,
    comparison_to_markdown,
)


def test_compare_run_manifests_ranks_and_warns_on_mixed_provenance(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_manifest(
        runs_dir / "run-a" / "manifest.json",
        run_id="run-a",
        sharpe=0.25,
        total_return=0.04,
        config_sha256="config-a",
        code_commit="commit-a",
        source="synthetic",
        dataset_id=None,
        dirty=False,
    )
    _write_manifest(
        runs_dir / "run-b" / "manifest.json",
        run_id="run-b",
        sharpe=0.80,
        total_return=0.10,
        config_sha256="config-b",
        code_commit="commit-b",
        source="csv_snapshot",
        dataset_id="golden-v1",
        dirty=True,
    )

    comparison = compare_run_manifests(runs_dir, metric="sharpe")
    payload = comparison_to_dict(comparison)

    assert comparison.run_count == 2
    assert [row.run_id for row in comparison.rows] == ["run-b", "run-a"]
    assert payload["summary"]["unique_configs"] == 2
    assert payload["summary"]["unique_code_commits"] == 2
    assert payload["rows"][0]["dataset_id"] == "golden-v1"
    assert "Compared runs use different config hashes." in comparison.warnings
    assert "Compared runs use different git commits." in comparison.warnings
    assert "At least one compared run was generated from a dirty git worktree." in comparison.warnings
    assert "Compared runs use different data sources." in comparison.warnings
    assert "Compared runs use different snapshot dataset ids." in comparison.warnings


def test_compare_run_manifests_treats_lower_cost_as_better(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_manifest(
        runs_dir / "expensive" / "manifest.json",
        run_id="expensive",
        sharpe=2.0,
        average_total_cost=0.004,
    )
    _write_manifest(
        runs_dir / "cheap" / "manifest.json",
        run_id="cheap",
        sharpe=0.1,
        average_total_cost=0.001,
    )

    comparison = compare_run_manifests(runs_dir, metric="average_total_cost")

    assert [row.run_id for row in comparison.rows] == ["cheap", "expensive"]


def test_compare_run_manifests_supports_single_manifest_limit_and_markdown(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, run_id="single-run", sharpe=1.1)

    comparison = compare_run_manifests(manifest_path, limit=1)
    rendered = comparison_to_markdown(comparison)

    assert comparison.run_count == 1
    assert [row.run_id for row in comparison.rows] == ["single-run"]
    assert "# Run Comparison" in rendered
    assert "| 1 | `single-run` |" in rendered


def test_compare_run_manifests_rejects_unknown_metric(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, run_id="single-run")

    with pytest.raises(ValueError, match="Unsupported comparison metric"):
        compare_run_manifests(manifest_path, metric="unknown")


def test_compare_runs_cli_writes_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    runs_dir = tmp_path / "runs"
    output_path = tmp_path / "comparison.json"
    _write_manifest(runs_dir / "run-a" / "manifest.json", run_id="run-a", sharpe=0.2)
    _write_manifest(runs_dir / "run-b" / "manifest.json", run_id="run-b", sharpe=0.6)

    exit_code = main(
        [
            "--compare-runs",
            str(runs_dir),
            "--json",
            "--limit",
            "1",
            "--output",
            str(output_path),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert f"Comparison: {output_path}" in output
    assert payload["run_count"] == 2
    assert [row["run_id"] for row in payload["rows"]] == ["run-b"]


def _write_manifest(
    path: Path,
    *,
    run_id: str,
    sharpe: float = 0.5,
    total_return: float = 0.05,
    ic_mean: float = 0.02,
    max_drawdown: float = -0.10,
    average_total_cost: float = 0.002,
    average_turnover: float = 1.2,
    config_sha256: str = "config-sha",
    code_commit: str = "code-sha",
    source: str = "synthetic",
    dataset_id: str | None = None,
    dirty: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "generated_at": "2026-06-17T00:00:00Z",
        "experiment": "comparison_test",
        "config": {
            "path": "configs/base.yaml",
            "copied_path": f"results/runs/{run_id}/config.yaml",
            "sha256": config_sha256,
        },
        "code": {
            "commit": code_commit,
            "branch": "main",
            "dirty": dirty,
        },
        "data": {
            "source": source,
            "snapshot_dataset_id": dataset_id,
            "observed_symbols": ["AAA", "BBB", "CCC"],
        },
        "artifacts": {
            "report_path": f"results/{run_id}.md",
            "experiments_path": "results/experiments.csv",
            "manifest_path": str(path),
        },
        "metrics": {
            "test": {
                "sharpe": sharpe,
                "total_return": total_return,
                "ic_mean": ic_mean,
                "max_drawdown": max_drawdown,
                "average_total_cost": average_total_cost,
                "average_turnover": average_turnover,
            },
            "full": {
                "sharpe": sharpe,
                "total_return": total_return,
            },
        },
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")
