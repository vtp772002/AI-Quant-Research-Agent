from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import hashlib
import json
import re

from quant_research_agent.experiment_registry import ExperimentRunRecord, list_runs, record_to_dict

GOVERNANCE_SCHEMA_VERSION = "registry_governance_v1"
DEFAULT_REGISTRY_OWNER = "local-research-operator"
DEFAULT_MINIMUM_RETENTION_DAYS = 365


@dataclass(frozen=True)
class RegistryExport:
    exported_at: str
    run_count: int
    output_dir: Path
    records_path: Path
    manifest_path: Path
    postgres_sql_path: Path
    governance_manifest_path: Path
    hash_chain_path: Path
    warnings: list[str]


@dataclass(frozen=True)
class RegistryGovernanceVerification:
    valid: bool
    manifest_path: Path
    checked_files: list[Path]
    errors: list[str]


def export_registry_snapshot(
    registry_path: Path,
    output_dir: Path,
    postgres_table: str = "experiment_runs",
    limit: int = 1000,
    owner: str = DEFAULT_REGISTRY_OWNER,
    minimum_retention_days: int = DEFAULT_MINIMUM_RETENTION_DAYS,
    previous_governance_manifest: Path | None = None,
) -> RegistryExport:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", postgres_table):
        raise ValueError("postgres_table must be a simple SQL identifier")
    owner = owner.strip()
    if not owner:
        raise ValueError("owner must not be blank")
    if minimum_retention_days <= 0:
        raise ValueError("minimum_retention_days must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = list_runs(registry_path, limit=limit)
    records_path = output_dir / "experiment_runs.ndjson"
    manifest_path = output_dir / "registry_export_manifest.json"
    postgres_sql_path = output_dir / "postgres_upsert_experiment_runs.sql"
    governance_manifest_path = output_dir / "registry_governance_manifest.json"
    hash_chain_path = output_dir / "registry_hash_chain.ndjson"
    exported_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    records_path.write_text(
        "".join(json.dumps(record_to_dict(record), sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    postgres_sql_path.write_text(_postgres_upsert_sql(records, postgres_table), encoding="utf-8")
    hash_chain_path.write_text(_hash_chain_ndjson(records), encoding="utf-8")
    previous_manifest_sha256 = _file_sha256(previous_governance_manifest) if previous_governance_manifest else None
    governance_manifest = _governance_manifest(
        exported_at=exported_at,
        registry_path=registry_path,
        output_dir=output_dir,
        records=records,
        records_path=records_path,
        postgres_sql_path=postgres_sql_path,
        hash_chain_path=hash_chain_path,
        owner=owner,
        minimum_retention_days=minimum_retention_days,
        previous_manifest_sha256=previous_manifest_sha256,
    )
    governance_manifest_path.write_text(
        json.dumps(governance_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "exported_at": exported_at,
        "source_registry_path": str(registry_path),
        "run_count": len(records),
        "records_path": str(records_path),
        "postgres_sql_path": str(postgres_sql_path),
        "governance_manifest_path": str(governance_manifest_path),
        "hash_chain_path": str(hash_chain_path),
        "format": "ndjson",
        "artifact_hashes": {
            "records_sha256": _file_sha256(records_path),
            "postgres_sql_sha256": _file_sha256(postgres_sql_path),
            "hash_chain_sha256": _file_sha256(hash_chain_path),
            "governance_manifest_sha256": _file_sha256(governance_manifest_path),
        },
        "warnings": [
            "This export includes immutable governance evidence, but it does not apply managed Postgres migrations or object-lock storage policy by itself."
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return RegistryExport(
        exported_at=exported_at,
        run_count=len(records),
        output_dir=output_dir,
        records_path=records_path,
        manifest_path=manifest_path,
        postgres_sql_path=postgres_sql_path,
        governance_manifest_path=governance_manifest_path,
        hash_chain_path=hash_chain_path,
        warnings=list(manifest["warnings"]),
    )


def registry_export_to_dict(export: RegistryExport) -> dict[str, object]:
    return {
        "exported_at": export.exported_at,
        "run_count": export.run_count,
        "output_dir": str(export.output_dir),
        "records_path": str(export.records_path),
        "manifest_path": str(export.manifest_path),
        "postgres_sql_path": str(export.postgres_sql_path),
        "governance_manifest_path": str(export.governance_manifest_path),
        "hash_chain_path": str(export.hash_chain_path),
        "warnings": export.warnings,
    }


def registry_governance_verification_to_dict(verification: RegistryGovernanceVerification) -> dict[str, object]:
    return {
        "valid": verification.valid,
        "manifest_path": str(verification.manifest_path),
        "checked_files": [str(path) for path in verification.checked_files],
        "errors": verification.errors,
    }


def verify_registry_governance_pack(output_dir: Path) -> RegistryGovernanceVerification:
    manifest_path = output_dir / "registry_governance_manifest.json"
    errors: list[str] = []
    checked_files: list[Path] = []
    if not manifest_path.exists():
        return RegistryGovernanceVerification(
            valid=False,
            manifest_path=manifest_path,
            checked_files=[],
            errors=[f"{manifest_path} does not exist"],
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return RegistryGovernanceVerification(
            valid=False,
            manifest_path=manifest_path,
            checked_files=[],
            errors=[f"governance manifest is not valid JSON: {exc.msg}"],
        )
    if not isinstance(manifest, dict):
        return RegistryGovernanceVerification(
            valid=False,
            manifest_path=manifest_path,
            checked_files=[],
            errors=["governance manifest must be a JSON object"],
        )
    if manifest.get("schema_version") != GOVERNANCE_SCHEMA_VERSION:
        errors.append("governance manifest schema_version is unsupported")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("governance manifest artifacts must be an object")
        artifacts = {}

    artifact_paths: dict[str, Path] = {}
    for key in ["records", "postgres_sql", "hash_chain"]:
        artifact = artifacts.get(key)
        if not isinstance(artifact, dict):
            errors.append(f"artifact {key} is missing")
            continue
        path_value = artifact.get("path")
        expected_sha256 = artifact.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected_sha256, str):
            errors.append(f"artifact {key} must include path and sha256")
            continue
        path = output_dir / path_value
        artifact_paths[key] = path
        checked_files.append(path)
        if not path.exists():
            errors.append(f"artifact {key} does not exist at {path}")
            continue
        actual_sha256 = _file_sha256(path)
        if actual_sha256 != expected_sha256:
            errors.append(f"artifact {key} sha256 mismatch")

    records_path = artifact_paths.get("records")
    hash_chain_path = artifact_paths.get("hash_chain")
    if records_path is not None and hash_chain_path is not None and records_path.exists() and hash_chain_path.exists():
        try:
            errors.extend(_verify_hash_chain(records_path, hash_chain_path))
            final_chain_hash = _final_chain_hash(hash_chain_path)
            if manifest.get("final_chain_hash") != final_chain_hash:
                errors.append("governance manifest final_chain_hash mismatch")
        except json.JSONDecodeError as exc:
            errors.append(f"hash chain verification failed: invalid JSON ({exc.msg})")

    return RegistryGovernanceVerification(
        valid=not errors,
        manifest_path=manifest_path,
        checked_files=checked_files,
        errors=errors,
    )


def _postgres_upsert_sql(records: list[ExperimentRunRecord], table: str) -> str:
    lines = [
        "-- Offline Postgres handoff generated from the local SQLite registry.",
        "-- Review table ownership, migrations, indexes, and retention policy before applying.",
        f"-- Records: {len(records)}",
        "",
        f"CREATE TABLE IF NOT EXISTS {table} (",
        "    run_id TEXT PRIMARY KEY,",
        "    payload JSONB NOT NULL,",
        "    generated_at TIMESTAMPTZ NOT NULL,",
        "    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        ");",
        "",
    ]
    for record in records:
        run_id = _sql_literal(record.run_id)
        generated_at = _sql_literal(record.generated_at)
        payload = _sql_literal(json.dumps(record_to_dict(record), sort_keys=True))
        lines.extend(
            [
                f"INSERT INTO {table} (run_id, payload, generated_at)",
                f"VALUES ('{run_id}', '{payload}'::jsonb, '{generated_at}'::timestamptz)",
                "ON CONFLICT (run_id) DO UPDATE SET",
                "    payload = EXCLUDED.payload,",
                "    generated_at = EXCLUDED.generated_at,",
                "    updated_at = NOW();",
                "",
            ]
        )
    return "\n".join(lines)


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _governance_manifest(
    *,
    exported_at: str,
    registry_path: Path,
    output_dir: Path,
    records: list[ExperimentRunRecord],
    records_path: Path,
    postgres_sql_path: Path,
    hash_chain_path: Path,
    owner: str,
    minimum_retention_days: int,
    previous_manifest_sha256: str | None,
) -> dict[str, object]:
    final_chain_hash = _final_chain_hash(hash_chain_path)
    return {
        "schema_version": GOVERNANCE_SCHEMA_VERSION,
        "exported_at": exported_at,
        "source_registry_path": str(registry_path),
        "run_count": len(records),
        "owner": owner,
        "retention": {
            "minimum_days": minimum_retention_days,
            "delete_requires": "human review, successor governance pack, and recorded rationale",
            "mutable_source": "SQLite registry remains local working storage; this pack is the immutable evidence handoff.",
        },
        "previous_governance_manifest_sha256": previous_manifest_sha256,
        "final_chain_hash": final_chain_hash,
        "artifacts": {
            "records": {
                "path": _relative_artifact_path(output_dir, records_path),
                "sha256": _file_sha256(records_path),
                "format": "ndjson",
            },
            "postgres_sql": {
                "path": _relative_artifact_path(output_dir, postgres_sql_path),
                "sha256": _file_sha256(postgres_sql_path),
                "format": "sql",
            },
            "hash_chain": {
                "path": _relative_artifact_path(output_dir, hash_chain_path),
                "sha256": _file_sha256(hash_chain_path),
                "format": "ndjson",
            },
        },
        "family_evidence": [_family_evidence(record) for record in records],
        "warnings": [
            "Governance evidence is advisory unless the output directory is stored in an object-lock or equivalent immutable store.",
            "Family promotion remains invalid if records outside this pack are later discovered for the same hypothesis family.",
        ],
    }


def _hash_chain_ndjson(records: list[ExperimentRunRecord]) -> str:
    lines: list[str] = []
    previous_hash: str | None = None
    for index, record in enumerate(records):
        record_payload = record_to_dict(record)
        record_sha256 = _payload_sha256(record_payload)
        chain_payload = {
            "index": index,
            "run_id": record.run_id,
            "record_sha256": record_sha256,
            "previous_chain_hash": previous_hash,
            "family_evidence": _family_evidence(record),
        }
        chain_hash = _payload_sha256(chain_payload)
        chain_row = {**chain_payload, "chain_hash": chain_hash}
        lines.append(json.dumps(chain_row, sort_keys=True))
        previous_hash = chain_hash
    return "\n".join(lines) + ("\n" if lines else "")


def _verify_hash_chain(records_path: Path, hash_chain_path: Path) -> list[str]:
    errors: list[str] = []
    record_lines = [line for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chain_lines = [line for line in hash_chain_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(record_lines) != len(chain_lines):
        return ["hash chain row count does not match records"]

    previous_hash: str | None = None
    for index, (record_line, chain_line) in enumerate(zip(record_lines, chain_lines, strict=True)):
        record_payload = json.loads(record_line)
        chain_row = json.loads(chain_line)
        expected_record_hash = _payload_sha256(record_payload)
        if chain_row.get("index") != index:
            errors.append(f"hash chain index mismatch at row {index}")
        if chain_row.get("run_id") != record_payload.get("run_id"):
            errors.append(f"hash chain run_id mismatch at row {index}")
        if chain_row.get("record_sha256") != expected_record_hash:
            errors.append(f"hash chain record hash mismatch at row {index}")
        if chain_row.get("previous_chain_hash") != previous_hash:
            errors.append(f"hash chain previous hash mismatch at row {index}")
        chain_payload = {
            key: chain_row.get(key)
            for key in ["index", "run_id", "record_sha256", "previous_chain_hash", "family_evidence"]
        }
        expected_chain_hash = _payload_sha256(chain_payload)
        if chain_row.get("chain_hash") != expected_chain_hash:
            errors.append(f"hash chain hash mismatch at row {index}")
        previous_hash = chain_row.get("chain_hash") if isinstance(chain_row.get("chain_hash"), str) else None
    return errors


def _family_evidence(record: ExperimentRunRecord) -> dict[str, object]:
    validity = record.metrics.get("research_validity")
    if not isinstance(validity, dict):
        validity = {}
    return {
        "run_id": record.run_id,
        "experiment_family_id": record.experiment_family_id,
        "hypothesis_id": record.hypothesis_id,
        "candidate_id": record.candidate_id,
        "selection_policy": record.selection_policy,
        "run_validity_verdict": validity.get("verdict"),
        "holdout_ic_p_value": validity.get("agent_p_value"),
        "holdout_ic_q_value": validity.get("agent_q_value"),
    }


def _final_chain_hash(hash_chain_path: Path) -> str | None:
    lines = [line for line in hash_chain_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    last = json.loads(lines[-1])
    value = last.get("chain_hash")
    return value if isinstance(value, str) else None


def _relative_artifact_path(output_dir: Path, artifact_path: Path) -> str:
    try:
        return str(artifact_path.relative_to(output_dir))
    except ValueError:
        return artifact_path.name


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
