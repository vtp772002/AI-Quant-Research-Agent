from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import json
import re

from quant_research_agent.experiment_registry import ExperimentRunRecord, list_runs, record_to_dict


@dataclass(frozen=True)
class RegistryExport:
    exported_at: str
    run_count: int
    output_dir: Path
    records_path: Path
    manifest_path: Path
    postgres_sql_path: Path
    warnings: list[str]


def export_registry_snapshot(
    registry_path: Path,
    output_dir: Path,
    postgres_table: str = "experiment_runs",
    limit: int = 1000,
) -> RegistryExport:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", postgres_table):
        raise ValueError("postgres_table must be a simple SQL identifier")
    output_dir.mkdir(parents=True, exist_ok=True)
    records = list_runs(registry_path, limit=limit)
    records_path = output_dir / "experiment_runs.ndjson"
    manifest_path = output_dir / "registry_export_manifest.json"
    postgres_sql_path = output_dir / "postgres_upsert_experiment_runs.sql"
    exported_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    records_path.write_text(
        "".join(json.dumps(record_to_dict(record), sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    postgres_sql_path.write_text(_postgres_upsert_sql(records, postgres_table), encoding="utf-8")
    manifest = {
        "exported_at": exported_at,
        "source_registry_path": str(registry_path),
        "run_count": len(records),
        "records_path": str(records_path),
        "postgres_sql_path": str(postgres_sql_path),
        "format": "ndjson",
        "warnings": [
            "This export is an offline handoff artifact; it does not replace a managed Postgres migration or object-lock storage policy."
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
        "warnings": export.warnings,
    }


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
