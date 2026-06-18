from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_research_agent.experiment_family import (
    compare_experiment_family,
    family_comparison_to_dict,
    family_comparison_to_markdown,
)
from quant_research_agent.main import main


def test_compare_experiment_family_promotes_preregistered_run_with_family_qvalue(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_family_manifest(
        runs_dir / "base" / "manifest.json",
        run_id="base-run",
        family_id="family-a",
        candidate_id="base",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.01,
    )
    _write_family_manifest(
        runs_dir / "explore" / "manifest.json",
        run_id="explore-run",
        family_id="family-a",
        candidate_id="explore",
        selection_policy="exploratory",
        run_verdict="PROMOTE",
        p_value=0.20,
    )

    comparison = compare_experiment_family(runs_dir, family_id="family-a", fdr_alpha=0.10)
    payload = family_comparison_to_dict(comparison)

    assert comparison.family_id == "family-a"
    assert comparison.run_count == 2
    assert payload["summary"]["pre_registered_count"] == 1
    by_run = {row.run_id: row for row in comparison.rows}
    assert by_run["base-run"].family_q_value == pytest.approx(0.02)
    assert by_run["base-run"].family_verdict == "FAMILY_PROMOTE"
    assert by_run["explore-run"].family_verdict == "FAMILY_REJECT"
    assert any("selection policy exploratory is not pre_registered" in reason for reason in by_run["explore-run"].reasons)
    assert any("family q-value" in reason for reason in by_run["explore-run"].reasons)


def test_compare_experiment_family_rejects_run_level_reject_and_family_qvalue_failure(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_family_manifest(
        runs_dir / "rejected" / "manifest.json",
        run_id="rejected-run",
        family_id="family-a",
        candidate_id="rejected",
        selection_policy="pre_registered",
        run_verdict="REJECT",
        p_value=0.001,
    )
    _write_family_manifest(
        runs_dir / "weak" / "manifest.json",
        run_id="weak-run",
        family_id="family-a",
        candidate_id="weak",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.20,
    )

    comparison = compare_experiment_family(runs_dir, family_id="family-a", fdr_alpha=0.10)
    by_run = {row.run_id: row for row in comparison.rows}

    assert by_run["rejected-run"].family_verdict == "FAMILY_REJECT"
    assert "run-level validity verdict is REJECT" in by_run["rejected-run"].reasons
    assert by_run["weak-run"].family_verdict == "FAMILY_REJECT"
    assert any("family q-value" in reason for reason in by_run["weak-run"].reasons)


def test_compare_experiment_family_reviews_missing_evidence_metadata_and_mixed_provenance(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_family_manifest(
        runs_dir / "missing-evidence" / "manifest.json",
        run_id="missing-evidence",
        family_id=None,
        candidate_id=None,
        selection_policy=None,
        run_verdict="PROMOTE",
        p_value=None,
        config_sha256="config-a",
        source="synthetic",
        dataset_id=None,
        dirty=False,
    )
    _write_family_manifest(
        runs_dir / "dirty" / "manifest.json",
        run_id="dirty-run",
        family_id="family-b",
        candidate_id="dirty",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.01,
        config_sha256="config-b",
        source="csv_snapshot",
        dataset_id="golden-v1",
        dirty=True,
    )

    comparison = compare_experiment_family(runs_dir, fdr_alpha=0.10)
    by_run = {row.run_id: row for row in comparison.rows}

    assert by_run["missing-evidence"].family_verdict == "FAMILY_REVIEW"
    assert by_run["missing-evidence"].agent_p_value == 1.0
    assert "agent_signal p-value evidence is missing" in by_run["missing-evidence"].reasons
    assert "family metadata is missing" in by_run["missing-evidence"].reasons
    assert by_run["dirty-run"].family_verdict == "FAMILY_REVIEW"
    assert "Compared family rows use different config hashes." in comparison.warnings
    assert "At least one family row was generated from a dirty git worktree." in comparison.warnings
    assert "Compared family rows use different data sources." in comparison.warnings
    assert "Compared family rows use different snapshot dataset ids." in comparison.warnings


def test_compare_experiment_family_reviews_multiple_preregistered_candidates(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_family_manifest(
        runs_dir / "base" / "manifest.json",
        run_id="base-run",
        family_id="family-a",
        candidate_id="base",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.01,
    )
    _write_family_manifest(
        runs_dir / "alt" / "manifest.json",
        run_id="alt-run",
        family_id="family-a",
        candidate_id="alt",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.02,
    )

    comparison = compare_experiment_family(runs_dir, family_id="family-a", fdr_alpha=0.10)

    assert {row.family_verdict for row in comparison.rows} == {"FAMILY_REVIEW"}
    assert "Multiple pre-registered candidates exist in this family." in comparison.warnings


def test_compare_experiment_family_renders_markdown_and_json(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    _write_family_manifest(
        manifest_path,
        run_id="single-run",
        family_id="family-a",
        candidate_id="base",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.01,
    )

    comparison = compare_experiment_family(manifest_path, family_id="family-a")
    rendered = family_comparison_to_markdown(comparison)
    payload = family_comparison_to_dict(comparison)

    assert "# Experiment Family Comparison" in rendered
    assert "FAMILY_PROMOTE" in rendered
    assert "| `single-run` | `base` | pre_registered | PROMOTE | 0.0100 | 0.0100 | FAMILY_PROMOTE |" in rendered
    assert payload["rows"][0]["run_id"] == "single-run"
    assert payload["rows"][0]["family_verdict"] == "FAMILY_PROMOTE"


def test_compare_experiment_family_rejects_invalid_alpha(tmp_path: Path):
    _write_family_manifest(tmp_path / "manifest.json", run_id="single-run")

    with pytest.raises(ValueError, match="family_fdr_alpha must be greater than 0 and at most 0.25"):
        compare_experiment_family(tmp_path / "manifest.json", fdr_alpha=0.30)


def test_compare_family_cli_writes_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    runs_dir = tmp_path / "runs"
    output_path = tmp_path / "family.json"
    _write_family_manifest(
        runs_dir / "base" / "manifest.json",
        run_id="base-run",
        family_id="family-a",
        candidate_id="base",
        selection_policy="pre_registered",
        run_verdict="PROMOTE",
        p_value=0.01,
    )

    exit_code = main(
        [
            "--compare-family",
            str(runs_dir),
            "--family-id",
            "family-a",
            "--json",
            "--output",
            str(output_path),
        ]
    )
    output = capsys.readouterr().out
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert f"Family comparison: {output_path}" in output
    assert payload["family_id"] == "family-a"
    assert payload["rows"][0]["family_verdict"] == "FAMILY_PROMOTE"


def test_compare_family_cli_rejects_invalid_alpha(tmp_path: Path):
    _write_family_manifest(tmp_path / "manifest.json", run_id="single-run")

    with pytest.raises(ValueError, match="family_fdr_alpha must be greater than 0 and at most 0.25"):
        main(
            [
                "--compare-family",
                str(tmp_path / "manifest.json"),
                "--family-fdr-alpha",
                "0.30",
            ]
        )


def _write_family_manifest(
    path: Path,
    *,
    run_id: str,
    family_id: str | None = "family-a",
    hypothesis_id: str | None = "hypothesis-a",
    candidate_id: str | None = "base",
    selection_policy: str | None = "pre_registered",
    run_verdict: str = "PROMOTE",
    p_value: float | None = 0.01,
    holdout_ic: float = 0.05,
    holdout_sharpe: float = 1.25,
    holdout_return: float = 0.10,
    config_sha256: str = "config-sha",
    code_commit: str = "code-sha",
    source: str = "synthetic",
    dataset_id: str | None = None,
    dirty: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidates = []
    if p_value is not None:
        candidates.append(
            {
                "name": "agent_signal",
                "family": "primary",
                "holdout_observations": 40,
                "holdout_sharpe": holdout_sharpe,
                "holdout_ic_mean": holdout_ic,
                "holdout_ic_tstat": 2.0,
                "holdout_total_return": holdout_return,
                "p_value": p_value,
                "q_value": p_value,
            }
        )
    manifest = {
        "run_id": run_id,
        "generated_at": "2026-06-18T00:00:00Z",
        "experiment": "family_test",
        "experiment_family": {
            "family_id": family_id,
            "hypothesis_id": hypothesis_id,
            "candidate_id": candidate_id,
            "selection_policy": selection_policy,
        },
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
            "observed_symbols": ["AAA", "BBB"],
        },
        "artifacts": {
            "report_path": f"results/{run_id}.md",
            "experiments_path": "results/experiments.csv",
            "manifest_path": str(path),
        },
        "metrics": {
            "test": {"sharpe": 1.0, "total_return": 0.08, "ic_mean": 0.03},
            "holdout": {
                "sharpe": holdout_sharpe,
                "total_return": holdout_return,
                "ic_mean": holdout_ic,
            },
            "full": {"sharpe": 1.0, "total_return": 0.08},
            "research_validity": {
                "verdict": run_verdict,
                "candidates": candidates,
            },
        },
        "research_validity": {
            "verdict": run_verdict,
            "candidates": candidates,
        },
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
