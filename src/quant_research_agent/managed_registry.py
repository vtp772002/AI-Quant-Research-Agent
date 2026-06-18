from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import copy2
from typing import Any

import hashlib
import json
import re

from quant_research_agent.registry_export import verify_registry_governance_pack


MANAGED_REGISTRY_SCHEMA_VERSION = "managed_registry_deployment_v1"
DEFAULT_OBJECT_PREFIX = "research/registry"
DEFAULT_POSTGRES_SCHEMA = "research_registry"
DEFAULT_POSTGRES_TABLE = "experiment_runs"


@dataclass(frozen=True)
class ManagedRegistryDeployment:
    staged_at: str
    output_dir: Path
    deployment_manifest_path: Path
    postgres_apply_plan_path: Path
    object_lock_inventory_path: Path
    object_store_dir: Path
    object_count: int
    warnings: list[str]


@dataclass(frozen=True)
class ManagedRegistryVerification:
    valid: bool
    deployment_manifest_path: Path
    checked_files: list[Path]
    errors: list[str]


def stage_managed_registry_deployment(
    *,
    governance_dir: Path,
    output_dir: Path,
    owner: str = "research-ops",
    postgres_schema: str = DEFAULT_POSTGRES_SCHEMA,
    postgres_table: str = DEFAULT_POSTGRES_TABLE,
    object_prefix: str = DEFAULT_OBJECT_PREFIX,
    retention_days: int = 730,
    legal_hold: bool = True,
) -> ManagedRegistryDeployment:
    owner = owner.strip()
    if not owner:
        raise ValueError("owner must not be blank")
    _validate_sql_identifier(postgres_schema, "postgres_schema")
    _validate_sql_identifier(postgres_table, "postgres_table")
    object_prefix = _normalize_object_prefix(object_prefix)
    if retention_days <= 0:
        raise ValueError("retention_days must be positive")

    governance_verification = verify_registry_governance_pack(governance_dir)
    if not governance_verification.valid:
        raise ValueError(
            "registry governance pack is invalid: "
            + "; ".join(governance_verification.errors)
        )

    governance_manifest_path = governance_dir / "registry_governance_manifest.json"
    governance_manifest = json.loads(governance_manifest_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    object_store_dir = output_dir / "object_store"
    object_store_dir.mkdir(parents=True, exist_ok=True)
    deployment_manifest_path = output_dir / "deployment_manifest.json"
    postgres_apply_plan_path = output_dir / "postgres_apply_plan.sql"
    object_lock_inventory_path = output_dir / "object_lock_inventory.ndjson"
    staged_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    retain_until = (datetime.now(UTC) + timedelta(days=retention_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    source_artifacts = _source_artifacts(governance_dir, governance_manifest_path, governance_manifest)
    object_rows = []
    for name, source_path in source_artifacts:
        object_key = f"{object_prefix}/{source_path.name}"
        object_path = object_store_dir / object_key
        object_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(source_path, object_path)
        object_rows.append(
            {
                "source_artifact": name,
                "object_key": object_key,
                "local_path": str(object_path.relative_to(output_dir)),
                "sha256": _file_sha256(object_path),
                "retention_days": retention_days,
                "retain_until": retain_until,
                "legal_hold": legal_hold,
            }
        )

    object_lock_inventory_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in object_rows),
        encoding="utf-8",
    )
    postgres_apply_plan_path.write_text(
        _postgres_apply_plan(
            governance_dir=governance_dir,
            governance_manifest_path=governance_manifest_path,
            postgres_sql_path=dict(source_artifacts)["postgres_sql"],
            postgres_schema=postgres_schema,
            postgres_table=postgres_table,
            staged_at=staged_at,
        ),
        encoding="utf-8",
    )
    deployment_manifest = {
        "schema_version": MANAGED_REGISTRY_SCHEMA_VERSION,
        "adapter": "local_dry_run",
        "status": "staged",
        "staged_at": staged_at,
        "owner": owner,
        "source_governance_dir": str(governance_dir),
        "source_governance_manifest_sha256": _file_sha256(governance_manifest_path),
        "source_governance_final_chain_hash": governance_manifest.get("final_chain_hash"),
        "source_run_count": governance_manifest.get("run_count"),
        "postgres": {
            "schema": postgres_schema,
            "table": postgres_table,
            "apply_plan_path": str(postgres_apply_plan_path.relative_to(output_dir)),
            "apply_plan_sha256": _file_sha256(postgres_apply_plan_path),
            "applied": False,
        },
        "object_lock": {
            "mode": "local_dry_run",
            "object_prefix": object_prefix,
            "retention_days": retention_days,
            "legal_hold": legal_hold,
            "retain_until": retain_until,
            "inventory_path": str(object_lock_inventory_path.relative_to(output_dir)),
            "inventory_sha256": _file_sha256(object_lock_inventory_path),
            "object_count": len(object_rows),
            "objects": object_rows,
        },
        "checks": {
            "governance_pack_verified": True,
            "requires_credentials": False,
            "network_calls": False,
            "external_mutation": False,
        },
        "warnings": [
            "This is a deterministic local dry-run deployment bundle; it does not apply Postgres migrations or enforce cloud object lock."
        ],
    }
    deployment_manifest_path.write_text(
        json.dumps(deployment_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ManagedRegistryDeployment(
        staged_at=staged_at,
        output_dir=output_dir,
        deployment_manifest_path=deployment_manifest_path,
        postgres_apply_plan_path=postgres_apply_plan_path,
        object_lock_inventory_path=object_lock_inventory_path,
        object_store_dir=object_store_dir,
        object_count=len(object_rows),
        warnings=list(deployment_manifest["warnings"]),
    )


def verify_managed_registry_deployment(output_dir: Path) -> ManagedRegistryVerification:
    manifest_path = output_dir / "deployment_manifest.json"
    checked_files: list[Path] = []
    errors: list[str] = []
    if not manifest_path.exists():
        return ManagedRegistryVerification(False, manifest_path, [], [f"{manifest_path} does not exist"])
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ManagedRegistryVerification(
            False,
            manifest_path,
            [],
            [f"deployment manifest is not valid JSON: {exc.msg}"],
        )
    if not isinstance(manifest, dict):
        return ManagedRegistryVerification(False, manifest_path, [], ["deployment manifest must be a JSON object"])
    if manifest.get("schema_version") != MANAGED_REGISTRY_SCHEMA_VERSION:
        errors.append("deployment manifest schema_version is unsupported")
    if manifest.get("adapter") != "local_dry_run":
        errors.append("deployment manifest adapter must be local_dry_run")
    checks = manifest.get("checks")
    if not isinstance(checks, dict):
        errors.append("deployment manifest checks must be an object")
    elif checks.get("requires_credentials") is not False or checks.get("network_calls") is not False:
        errors.append("deployment manifest must declare credential-free local execution")

    postgres = manifest.get("postgres")
    if isinstance(postgres, dict):
        _check_manifest_artifact(
            output_dir=output_dir,
            path_value=postgres.get("apply_plan_path"),
            expected_sha256=postgres.get("apply_plan_sha256"),
            label="postgres apply plan",
            checked_files=checked_files,
            errors=errors,
        )
    else:
        errors.append("deployment manifest postgres must be an object")

    object_lock = manifest.get("object_lock")
    if isinstance(object_lock, dict):
        inventory_path = _check_manifest_artifact(
            output_dir=output_dir,
            path_value=object_lock.get("inventory_path"),
            expected_sha256=object_lock.get("inventory_sha256"),
            label="object lock inventory",
            checked_files=checked_files,
            errors=errors,
        )
        objects = object_lock.get("objects")
        if not isinstance(objects, list):
            errors.append("deployment manifest object_lock.objects must be a list")
        else:
            if object_lock.get("object_count") != len(objects):
                errors.append("object lock object_count does not match objects")
            errors.extend(_verify_inventory_objects(output_dir, inventory_path, objects, checked_files))
    else:
        errors.append("deployment manifest object_lock must be an object")

    return ManagedRegistryVerification(
        valid=not errors,
        deployment_manifest_path=manifest_path,
        checked_files=checked_files,
        errors=errors,
    )


def managed_registry_deployment_to_dict(deployment: ManagedRegistryDeployment) -> dict[str, object]:
    return {
        "staged_at": deployment.staged_at,
        "output_dir": str(deployment.output_dir),
        "deployment_manifest_path": str(deployment.deployment_manifest_path),
        "postgres_apply_plan_path": str(deployment.postgres_apply_plan_path),
        "object_lock_inventory_path": str(deployment.object_lock_inventory_path),
        "object_store_dir": str(deployment.object_store_dir),
        "object_count": deployment.object_count,
        "warnings": deployment.warnings,
    }


def managed_registry_verification_to_dict(verification: ManagedRegistryVerification) -> dict[str, object]:
    return {
        "valid": verification.valid,
        "deployment_manifest_path": str(verification.deployment_manifest_path),
        "checked_files": [str(path) for path in verification.checked_files],
        "errors": verification.errors,
    }


def _source_artifacts(
    governance_dir: Path,
    governance_manifest_path: Path,
    governance_manifest: dict[str, Any],
) -> list[tuple[str, Path]]:
    artifacts = governance_manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("governance manifest artifacts must be an object")
    required = [
        ("governance_manifest", governance_manifest_path),
        ("records", _governance_artifact_path(governance_dir, artifacts, "records")),
        ("postgres_sql", _governance_artifact_path(governance_dir, artifacts, "postgres_sql")),
        ("hash_chain", _governance_artifact_path(governance_dir, artifacts, "hash_chain")),
    ]
    for name, path in required:
        if not path.exists():
            raise ValueError(f"governance artifact {name} does not exist at {path}")
    return required


def _governance_artifact_path(governance_dir: Path, artifacts: dict[str, Any], name: str) -> Path:
    entry = artifacts.get(name)
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        raise ValueError(f"governance artifact {name} is missing path")
    return governance_dir / entry["path"]


def _postgres_apply_plan(
    *,
    governance_dir: Path,
    governance_manifest_path: Path,
    postgres_sql_path: Path,
    postgres_schema: str,
    postgres_table: str,
    staged_at: str,
) -> str:
    source_sql = postgres_sql_path.read_text(encoding="utf-8")
    return "\n".join(
        [
            "-- Managed registry local dry-run apply plan.",
            "-- This file is not executed by the adapter.",
            f"-- Staged at: {staged_at}",
            f"-- Source governance dir: {governance_dir}",
            f"-- Source governance manifest: {governance_manifest_path}",
            f"CREATE SCHEMA IF NOT EXISTS {postgres_schema};",
            f"-- Target table: {postgres_schema}.{postgres_table}",
            "BEGIN;",
            f"SET search_path TO {postgres_schema}, public;",
            source_sql,
            "COMMIT;",
            "",
        ]
    )


def _check_manifest_artifact(
    *,
    output_dir: Path,
    path_value: object,
    expected_sha256: object,
    label: str,
    checked_files: list[Path],
    errors: list[str],
) -> Path | None:
    if not isinstance(path_value, str) or not isinstance(expected_sha256, str):
        errors.append(f"{label} must include path and sha256")
        return None
    path = output_dir / path_value
    checked_files.append(path)
    if not path.exists():
        errors.append(f"{label} does not exist at {path}")
        return path
    actual_sha256 = _file_sha256(path)
    if actual_sha256 != expected_sha256:
        errors.append(f"{label} sha256 mismatch")
    return path


def _verify_inventory_objects(
    output_dir: Path,
    inventory_path: Path | None,
    objects: list[object],
    checked_files: list[Path],
) -> list[str]:
    errors: list[str] = []
    inventory_rows = []
    if inventory_path is not None and inventory_path.exists():
        try:
            inventory_rows = [
                json.loads(line)
                for line in inventory_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except json.JSONDecodeError as exc:
            errors.append(f"object lock inventory is not valid JSON: {exc.msg}")
    if inventory_rows and inventory_rows != objects:
        errors.append("object lock inventory rows do not match deployment manifest objects")

    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            errors.append(f"object lock object {index} must be an object")
            continue
        local_path = item.get("local_path")
        expected_sha256 = item.get("sha256")
        if not isinstance(local_path, str) or not isinstance(expected_sha256, str):
            errors.append(f"object lock object {index} must include local_path and sha256")
            continue
        path = output_dir / local_path
        checked_files.append(path)
        if not path.exists():
            errors.append(f"object lock object {index} does not exist at {path}")
            continue
        actual_sha256 = _file_sha256(path)
        if actual_sha256 != expected_sha256:
            errors.append(f"object lock object {index} sha256 mismatch")
    return errors


def _validate_sql_identifier(value: str, field_name: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"{field_name} must be a simple SQL identifier")


def _normalize_object_prefix(value: str) -> str:
    text = value.strip().strip("/")
    if not text:
        raise ValueError("object_prefix must not be blank")
    if ".." in text.split("/"):
        raise ValueError("object_prefix must not contain parent directory segments")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", text):
        raise ValueError("object_prefix contains unsupported characters")
    return text


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
