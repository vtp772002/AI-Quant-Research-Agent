from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_research_agent.experiment_registry import record_run
from quant_research_agent.main import main
from quant_research_agent.managed_registry import (
    stage_managed_registry_deployment,
    verify_managed_registry_deployment,
)
from quant_research_agent.registry_export import export_registry_snapshot


def test_stage_managed_registry_deployment_writes_verifiable_bundle(tmp_path: Path):
    governance_dir = _governance_pack(tmp_path)

    deployment = stage_managed_registry_deployment(
        governance_dir=governance_dir,
        output_dir=tmp_path / "managed",
        owner="research-ops",
        postgres_schema="research_registry",
        postgres_table="experiment_runs",
        object_prefix="research/registry",
        retention_days=730,
        legal_hold=True,
    )

    manifest = json.loads(deployment.deployment_manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "managed_registry_deployment_v1"
    assert manifest["adapter"] == "local_dry_run"
    assert manifest["checks"] == {
        "external_mutation": False,
        "governance_pack_verified": True,
        "network_calls": False,
        "requires_credentials": False,
    }
    assert manifest["postgres"]["applied"] is False
    assert manifest["object_lock"]["object_count"] == 4
    assert manifest["object_lock"]["retention_days"] == 730
    assert manifest["object_lock"]["legal_hold"] is True
    assert "CREATE SCHEMA IF NOT EXISTS research_registry" in deployment.postgres_apply_plan_path.read_text(
        encoding="utf-8"
    )

    verification = verify_managed_registry_deployment(deployment.output_dir)

    assert verification.valid
    assert verification.errors == []
    assert deployment.postgres_apply_plan_path in verification.checked_files
    assert deployment.object_lock_inventory_path in verification.checked_files


def test_stage_managed_registry_rejects_invalid_source_governance_pack(tmp_path: Path):
    governance_dir = _governance_pack(tmp_path)
    records_path = governance_dir / "experiment_runs.ndjson"
    line = json.loads(records_path.read_text(encoding="utf-8").splitlines()[0])
    line["candidate_id"] = "tampered"
    records_path.write_text(json.dumps(line, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="registry governance pack is invalid"):
        stage_managed_registry_deployment(governance_dir=governance_dir, output_dir=tmp_path / "managed")


def test_verify_managed_registry_detects_staged_object_tampering(tmp_path: Path):
    deployment = stage_managed_registry_deployment(
        governance_dir=_governance_pack(tmp_path),
        output_dir=tmp_path / "managed",
    )
    manifest = json.loads(deployment.deployment_manifest_path.read_text(encoding="utf-8"))
    first_object = deployment.output_dir / manifest["object_lock"]["objects"][0]["local_path"]
    first_object.write_text("tampered", encoding="utf-8")

    verification = verify_managed_registry_deployment(deployment.output_dir)

    assert not verification.valid
    assert any("object lock object 0 sha256 mismatch" in error for error in verification.errors)


def test_stage_managed_registry_rejects_unsafe_identifiers_and_prefix(tmp_path: Path):
    governance_dir = _governance_pack(tmp_path)
    with pytest.raises(ValueError, match="postgres_schema must be a simple SQL identifier"):
        stage_managed_registry_deployment(
            governance_dir=governance_dir,
            output_dir=tmp_path / "managed-schema",
            postgres_schema="bad-schema;",
        )
    with pytest.raises(ValueError, match="object_prefix must not contain parent directory"):
        stage_managed_registry_deployment(
            governance_dir=governance_dir,
            output_dir=tmp_path / "managed-prefix",
            object_prefix="research/../registry",
        )
    with pytest.raises(ValueError, match="retention_days must be positive"):
        stage_managed_registry_deployment(
            governance_dir=governance_dir,
            output_dir=tmp_path / "managed-retention",
            retention_days=0,
        )


def test_managed_registry_cli_stage_and_verify(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    governance_dir = _governance_pack(tmp_path)
    managed_dir = tmp_path / "managed"

    stage_code = main(
        [
            "--stage-managed-registry",
            str(managed_dir),
            "--registry-governance-dir",
            str(governance_dir),
            "--managed-registry-owner",
            "research-ops",
            "--managed-registry-retention-days",
            "730",
        ]
    )
    stage_payload = json.loads(capsys.readouterr().out)
    verify_code = main(["--verify-managed-registry", str(managed_dir)])
    verify_payload = json.loads(capsys.readouterr().out)

    assert stage_code == 0
    assert stage_payload["object_count"] == 4
    assert verify_code == 0
    assert verify_payload["valid"] is True
    assert verify_payload["errors"] == []


def _governance_pack(tmp_path: Path) -> Path:
    registry_path = tmp_path / "experiments.sqlite"
    record_run(registry_path, _manifest("run-001", tmp_path / "report.md"))
    export = export_registry_snapshot(
        registry_path,
        tmp_path / "registry_export",
        owner="research-ops",
        minimum_retention_days=730,
    )
    return export.output_dir


def _manifest(run_id: str, report_path: Path) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-06-18T00:00:00Z",
        "experiment": "managed_registry_test",
        "config": {
            "path": "configs/base.yaml",
            "copied_path": "results/runs/run-001/config.yaml",
            "sha256": "abc123",
        },
        "code": {
            "commit": "deadbeef",
            "branch": "main",
            "dirty": False,
        },
        "data": {
            "source": "synthetic",
            "snapshot_dataset_id": None,
            "observed_symbols": ["AAA", "BBB"],
        },
        "artifacts": {
            "report_path": str(report_path),
            "experiments_path": str(report_path.with_name("experiments.csv")),
            "manifest_path": str(report_path.with_name("manifest.json")),
        },
        "metrics": {
            "test": {
                "sharpe": 1.25,
                "total_return": 0.12,
                "ic_mean": 0.03,
                "max_drawdown": -0.08,
                "average_turnover": 1.1,
                "average_total_cost": 0.001,
            },
            "full": {
                "sharpe": 1.4,
                "total_return": 0.2,
            },
            "research_validity": {
                "verdict": "PROMOTE",
                "agent_p_value": 0.01,
                "agent_q_value": 0.02,
            },
        },
        "experiment_family": {
            "family_id": "managed-registry-family-v1",
            "hypothesis_id": "managed-registry-hypothesis",
            "candidate_id": run_id,
            "selection_policy": "pre_registered",
        },
    }
