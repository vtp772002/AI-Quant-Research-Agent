from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Connection, Row, connect
from typing import Any

import json


SCHEMA = """
CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    experiment TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    data_source TEXT NOT NULL,
    dataset_id TEXT,
    code_commit TEXT NOT NULL,
    code_branch TEXT NOT NULL,
    code_dirty INTEGER NOT NULL,
    report_path TEXT NOT NULL,
    experiments_path TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    test_sharpe REAL NOT NULL,
    test_total_return REAL NOT NULL,
    test_ic_mean REAL NOT NULL,
    test_max_drawdown REAL NOT NULL,
    test_average_turnover REAL NOT NULL,
    test_average_total_cost REAL NOT NULL,
    full_sharpe REAL NOT NULL,
    full_total_return REAL NOT NULL,
    metrics_json TEXT NOT NULL,
    data_json TEXT NOT NULL,
    artifacts_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiment_runs_generated_at
    ON experiment_runs(generated_at);

CREATE INDEX IF NOT EXISTS idx_experiment_runs_experiment
    ON experiment_runs(experiment);
"""


@dataclass(frozen=True)
class ExperimentRunRecord:
    run_id: str
    experiment: str
    generated_at: str
    config_sha256: str
    data_source: str
    dataset_id: str | None
    code_commit: str
    code_branch: str
    code_dirty: bool
    report_path: str
    experiments_path: str
    manifest_path: str
    test_sharpe: float
    test_total_return: float
    test_ic_mean: float
    test_max_drawdown: float
    test_average_turnover: float
    test_average_total_cost: float
    full_sharpe: float
    full_total_return: float
    metrics: dict[str, Any]
    data: dict[str, Any]
    artifacts: dict[str, Any]
    created_at: str


def initialize_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        connection.executescript(SCHEMA)


def record_run(path: Path, manifest: dict[str, Any]) -> ExperimentRunRecord:
    initialize_registry(path)
    record = record_from_manifest(manifest)
    with _connect(path) as connection:
        connection.execute(
            """
            INSERT INTO experiment_runs (
                run_id, experiment, generated_at, config_sha256, data_source,
                dataset_id, code_commit, code_branch, code_dirty, report_path,
                experiments_path, manifest_path, test_sharpe, test_total_return,
                test_ic_mean, test_max_drawdown, test_average_turnover,
                test_average_total_cost, full_sharpe, full_total_return,
                metrics_json, data_json, artifacts_json, created_at
            )
            VALUES (
                :run_id, :experiment, :generated_at, :config_sha256, :data_source,
                :dataset_id, :code_commit, :code_branch, :code_dirty, :report_path,
                :experiments_path, :manifest_path, :test_sharpe, :test_total_return,
                :test_ic_mean, :test_max_drawdown, :test_average_turnover,
                :test_average_total_cost, :full_sharpe, :full_total_return,
                :metrics_json, :data_json, :artifacts_json, :created_at
            )
            ON CONFLICT(run_id) DO UPDATE SET
                experiment = excluded.experiment,
                generated_at = excluded.generated_at,
                config_sha256 = excluded.config_sha256,
                data_source = excluded.data_source,
                dataset_id = excluded.dataset_id,
                code_commit = excluded.code_commit,
                code_branch = excluded.code_branch,
                code_dirty = excluded.code_dirty,
                report_path = excluded.report_path,
                experiments_path = excluded.experiments_path,
                manifest_path = excluded.manifest_path,
                test_sharpe = excluded.test_sharpe,
                test_total_return = excluded.test_total_return,
                test_ic_mean = excluded.test_ic_mean,
                test_max_drawdown = excluded.test_max_drawdown,
                test_average_turnover = excluded.test_average_turnover,
                test_average_total_cost = excluded.test_average_total_cost,
                full_sharpe = excluded.full_sharpe,
                full_total_return = excluded.full_total_return,
                metrics_json = excluded.metrics_json,
                data_json = excluded.data_json,
                artifacts_json = excluded.artifacts_json,
                created_at = excluded.created_at
            """,
            _db_params(record),
        )
    return record


def get_run(path: Path, run_id: str) -> ExperimentRunRecord | None:
    initialize_registry(path)
    with _connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM experiment_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    return _record_from_row(row) if row is not None else None


def list_runs(path: Path, limit: int = 20) -> list[ExperimentRunRecord]:
    initialize_registry(path)
    with _connect(path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM experiment_runs
            ORDER BY generated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_record_from_row(row) for row in rows]


def record_from_manifest(manifest: dict[str, Any]) -> ExperimentRunRecord:
    metrics = _as_dict(manifest.get("metrics"))
    test_metrics = _as_dict(metrics.get("test"))
    full_metrics = _as_dict(metrics.get("full"))
    data = _as_dict(manifest.get("data"))
    code = _as_dict(manifest.get("code"))
    artifacts = _as_dict(manifest.get("artifacts"))
    return ExperimentRunRecord(
        run_id=str(manifest["run_id"]),
        experiment=str(manifest["experiment"]),
        generated_at=str(manifest["generated_at"]),
        config_sha256=str(_as_dict(manifest["config"])["sha256"]),
        data_source=str(data.get("source", "unknown")),
        dataset_id=data.get("snapshot_dataset_id"),
        code_commit=str(code.get("commit", "unknown")),
        code_branch=str(code.get("branch", "unknown")),
        code_dirty=bool(code.get("dirty", False)),
        report_path=str(artifacts["report_path"]),
        experiments_path=str(artifacts["experiments_path"]),
        manifest_path=str(artifacts["manifest_path"]),
        test_sharpe=float(test_metrics.get("sharpe", 0.0)),
        test_total_return=float(test_metrics.get("total_return", 0.0)),
        test_ic_mean=float(test_metrics.get("ic_mean", 0.0)),
        test_max_drawdown=float(test_metrics.get("max_drawdown", 0.0)),
        test_average_turnover=float(test_metrics.get("average_turnover", 0.0)),
        test_average_total_cost=float(test_metrics.get("average_total_cost", 0.0)),
        full_sharpe=float(full_metrics.get("sharpe", 0.0)),
        full_total_return=float(full_metrics.get("total_return", 0.0)),
        metrics=metrics,
        data=data,
        artifacts=artifacts,
        created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def record_to_dict(record: ExperimentRunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "experiment": record.experiment,
        "generated_at": record.generated_at,
        "config_sha256": record.config_sha256,
        "data_source": record.data_source,
        "dataset_id": record.dataset_id,
        "code_commit": record.code_commit,
        "code_branch": record.code_branch,
        "code_dirty": record.code_dirty,
        "report_path": record.report_path,
        "experiments_path": record.experiments_path,
        "manifest_path": record.manifest_path,
        "test_sharpe": record.test_sharpe,
        "test_total_return": record.test_total_return,
        "test_ic_mean": record.test_ic_mean,
        "test_max_drawdown": record.test_max_drawdown,
        "test_average_turnover": record.test_average_turnover,
        "test_average_total_cost": record.test_average_total_cost,
        "full_sharpe": record.full_sharpe,
        "full_total_return": record.full_total_return,
        "metrics": record.metrics,
        "data": record.data,
        "artifacts": record.artifacts,
        "created_at": record.created_at,
    }


def _connect(path: Path) -> Connection:
    connection = connect(path)
    connection.row_factory = Row
    return connection


def _db_params(record: ExperimentRunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "experiment": record.experiment,
        "generated_at": record.generated_at,
        "config_sha256": record.config_sha256,
        "data_source": record.data_source,
        "dataset_id": record.dataset_id,
        "code_commit": record.code_commit,
        "code_branch": record.code_branch,
        "code_dirty": int(record.code_dirty),
        "report_path": record.report_path,
        "experiments_path": record.experiments_path,
        "manifest_path": record.manifest_path,
        "test_sharpe": record.test_sharpe,
        "test_total_return": record.test_total_return,
        "test_ic_mean": record.test_ic_mean,
        "test_max_drawdown": record.test_max_drawdown,
        "test_average_turnover": record.test_average_turnover,
        "test_average_total_cost": record.test_average_total_cost,
        "full_sharpe": record.full_sharpe,
        "full_total_return": record.full_total_return,
        "metrics_json": json.dumps(record.metrics, sort_keys=True),
        "data_json": json.dumps(record.data, sort_keys=True),
        "artifacts_json": json.dumps(record.artifacts, sort_keys=True),
        "created_at": record.created_at,
    }


def _record_from_row(row: Row) -> ExperimentRunRecord:
    return ExperimentRunRecord(
        run_id=str(row["run_id"]),
        experiment=str(row["experiment"]),
        generated_at=str(row["generated_at"]),
        config_sha256=str(row["config_sha256"]),
        data_source=str(row["data_source"]),
        dataset_id=row["dataset_id"],
        code_commit=str(row["code_commit"]),
        code_branch=str(row["code_branch"]),
        code_dirty=bool(row["code_dirty"]),
        report_path=str(row["report_path"]),
        experiments_path=str(row["experiments_path"]),
        manifest_path=str(row["manifest_path"]),
        test_sharpe=float(row["test_sharpe"]),
        test_total_return=float(row["test_total_return"]),
        test_ic_mean=float(row["test_ic_mean"]),
        test_max_drawdown=float(row["test_max_drawdown"]),
        test_average_turnover=float(row["test_average_turnover"]),
        test_average_total_cost=float(row["test_average_total_cost"]),
        full_sharpe=float(row["full_sharpe"]),
        full_total_return=float(row["full_total_return"]),
        metrics=json.loads(row["metrics_json"]),
        data=json.loads(row["data_json"]),
        artifacts=json.loads(row["artifacts_json"]),
        created_at=str(row["created_at"]),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
