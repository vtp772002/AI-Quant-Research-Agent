from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlite3 import Connection, Row, connect
from typing import Any
from uuid import uuid4

import json


JOB_STATUSES = {"queued", "running", "retryable", "completed", "dead_letter"}
COMPARISON_METRICS = {
    "sharpe",
    "total_return",
    "ic_mean",
    "max_drawdown",
    "average_total_cost",
    "average_turnover",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS research_jobs (
    job_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    config_paths_json TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    comparison_metric TEXT NOT NULL,
    result_limit INTEGER,
    attempts INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL,
    available_at TEXT NOT NULL,
    lease_owner TEXT,
    lease_token TEXT,
    lease_expires_at TEXT,
    result_json TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_jobs_claim
    ON research_jobs(status, available_at, lease_expires_at, created_at);

CREATE TABLE IF NOT EXISTS research_job_events (
    event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    worker_id TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES research_jobs(job_id)
);

CREATE INDEX IF NOT EXISTS idx_research_job_events_job
    ON research_job_events(job_id, event_sequence);
"""


@dataclass(frozen=True)
class ResearchJob:
    job_id: str
    idempotency_key: str
    status: str
    config_paths: list[str]
    output_dir: str
    comparison_metric: str
    limit: int | None
    attempts: int
    max_attempts: int
    available_at: str
    lease_owner: str | None
    lease_token: str | None
    lease_expires_at: str | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None
    created_at: str
    updated_at: str
    started_at: str | None
    completed_at: str | None


@dataclass(frozen=True)
class ResearchJobEvent:
    event_id: str
    job_id: str
    event_type: str
    from_status: str | None
    to_status: str
    worker_id: str | None
    detail: dict[str, Any]
    created_at: str


def initialize_research_job_queue(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        connection.executescript(SCHEMA)


def enqueue_research_job(
    path: Path,
    *,
    config_paths: list[Path],
    output_dir: Path,
    idempotency_key: str,
    comparison_metric: str = "sharpe",
    limit: int | None = None,
    max_attempts: int = 3,
    submitted_by: str | None = None,
    now: datetime | None = None,
) -> ResearchJob:
    if not config_paths:
        raise ValueError("at least one config path is required")
    if not idempotency_key.strip():
        raise ValueError("idempotency_key must not be blank")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive when provided")
    if comparison_metric not in COMPARISON_METRICS:
        raise ValueError(
            f"unsupported comparison_metric: {comparison_metric}"
        )
    initialize_research_job_queue(path)
    timestamp = _timestamp(now)
    config_values = [str(config_path) for config_path in config_paths]
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT * FROM research_jobs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            existing_job = _job_from_row(existing)
            expected_payload = (
                config_values,
                str(output_dir),
                comparison_metric,
                limit,
                max_attempts,
            )
            existing_payload = (
                existing_job.config_paths,
                existing_job.output_dir,
                existing_job.comparison_metric,
                existing_job.limit,
                existing_job.max_attempts,
            )
            if existing_payload != expected_payload:
                raise ValueError(
                    "idempotency key is already bound to a different job payload"
                )
            return existing_job
        job_id = uuid4().hex
        connection.execute(
            """
            INSERT INTO research_jobs (
                job_id, idempotency_key, status, config_paths_json, output_dir,
                comparison_metric, result_limit, attempts, max_attempts,
                available_at, created_at, updated_at
            )
            VALUES (?, ?, 'queued', ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                job_id,
                idempotency_key,
                json.dumps(config_values),
                str(output_dir),
                comparison_metric,
                limit,
                max_attempts,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        _append_event(
            connection,
            job_id=job_id,
            event_type="enqueued",
            from_status=None,
            to_status="queued",
            created_at=timestamp,
            detail={
                "idempotency_key": idempotency_key,
                "submitted_by": submitted_by,
            },
        )
        row = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    assert row is not None
    return _job_from_row(row)


def claim_research_job(
    path: Path,
    *,
    worker_id: str,
    lease_seconds: int = 300,
    now: datetime | None = None,
) -> ResearchJob | None:
    if not worker_id.strip():
        raise ValueError("worker_id must not be blank")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be positive")
    initialize_research_job_queue(path)
    current = now or datetime.now(UTC)
    timestamp = _timestamp(current)
    lease_expires_at = _timestamp(current + timedelta(seconds=lease_seconds))
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        exhausted = connection.execute(
            """
            SELECT *
            FROM research_jobs
            WHERE status = 'running'
              AND lease_expires_at <= ?
              AND attempts >= max_attempts
            ORDER BY created_at, rowid
            """,
            (timestamp,),
        ).fetchall()
        for expired in exhausted:
            expired_job_id = str(expired["job_id"])
            error = {
                "type": "LeaseExpired",
                "message": "worker lease expired after the final allowed attempt",
            }
            connection.execute(
                """
                UPDATE research_jobs
                SET status = 'dead_letter',
                    error_json = ?,
                    lease_owner = NULL,
                    lease_token = NULL,
                    lease_expires_at = NULL,
                    completed_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    json.dumps(error, sort_keys=True),
                    timestamp,
                    timestamp,
                    expired_job_id,
                ),
            )
            _append_event(
                connection,
                job_id=expired_job_id,
                event_type="dead_lettered",
                from_status="running",
                to_status="dead_letter",
                worker_id=expired["lease_owner"],
                created_at=timestamp,
                detail={
                    "attempts": int(expired["attempts"]),
                    "max_attempts": int(expired["max_attempts"]),
                    "error": error,
                },
            )
        row = connection.execute(
            """
            SELECT *
            FROM research_jobs
            WHERE
                attempts < max_attempts
                AND (
                    (status = 'queued' AND available_at <= ?)
                    OR (status = 'retryable' AND available_at <= ?)
                    OR (status = 'running' AND lease_expires_at <= ?)
                )
            ORDER BY created_at, rowid
            LIMIT 1
            """,
            (timestamp, timestamp, timestamp),
        ).fetchone()
        if row is None:
            return None
        job_id = str(row["job_id"])
        lease_token = uuid4().hex
        previous_status = str(row["status"])
        if previous_status == "running":
            _append_event(
                connection,
                job_id=job_id,
                event_type="lease_recovered",
                from_status="running",
                to_status="queued",
                worker_id=worker_id,
                created_at=timestamp,
                detail={
                    "expired_lease_owner": row["lease_owner"],
                    "expired_at": row["lease_expires_at"],
                },
            )
        connection.execute(
            """
            UPDATE research_jobs
            SET status = 'running',
                attempts = attempts + 1,
                lease_owner = ?,
                lease_token = ?,
                lease_expires_at = ?,
                started_at = COALESCE(started_at, ?),
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                worker_id,
                lease_token,
                lease_expires_at,
                timestamp,
                timestamp,
                job_id,
            ),
        )
        _append_event(
            connection,
            job_id=job_id,
            event_type="claimed",
            from_status=previous_status,
            to_status="running",
            worker_id=worker_id,
            created_at=timestamp,
            detail={"lease_expires_at": lease_expires_at},
        )
        claimed = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    assert claimed is not None
    return _job_from_row(claimed)


def complete_research_job(
    path: Path,
    *,
    job_id: str,
    lease_token: str,
    result: dict[str, Any],
    now: datetime | None = None,
) -> ResearchJob:
    initialize_research_job_queue(path)
    timestamp = _timestamp(now)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"research job not found: {job_id}")
        _require_active_lease(row, lease_token, timestamp)
        connection.execute(
            """
            UPDATE research_jobs
            SET status = 'completed',
                result_json = ?,
                error_json = NULL,
                lease_owner = NULL,
                lease_token = NULL,
                lease_expires_at = NULL,
                completed_at = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (json.dumps(result, sort_keys=True), timestamp, timestamp, job_id),
        )
        _append_event(
            connection,
            job_id=job_id,
            event_type="completed",
            from_status="running",
            to_status="completed",
            worker_id=row["lease_owner"],
            created_at=timestamp,
            detail={"result": result},
        )
        completed = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    assert completed is not None
    return _job_from_row(completed)


def fail_research_job(
    path: Path,
    *,
    job_id: str,
    lease_token: str,
    error: dict[str, Any],
    retry_delay_seconds: int = 0,
    now: datetime | None = None,
) -> ResearchJob:
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds must not be negative")
    initialize_research_job_queue(path)
    current = now or datetime.now(UTC)
    timestamp = _timestamp(current)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"research job not found: {job_id}")
        _require_active_lease(row, lease_token, timestamp)
        attempts = int(row["attempts"])
        max_attempts = int(row["max_attempts"])
        if attempts >= max_attempts:
            next_status = "dead_letter"
            event_type = "dead_lettered"
            available_at = timestamp
            completed_at: str | None = timestamp
        else:
            next_status = "retryable"
            event_type = "retry_scheduled"
            available_at = _timestamp(
                current + timedelta(seconds=retry_delay_seconds)
            )
            completed_at = None
        connection.execute(
            """
            UPDATE research_jobs
            SET status = ?,
                available_at = ?,
                result_json = NULL,
                error_json = ?,
                lease_owner = NULL,
                lease_token = NULL,
                lease_expires_at = NULL,
                completed_at = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                next_status,
                available_at,
                json.dumps(error, sort_keys=True),
                completed_at,
                timestamp,
                job_id,
            ),
        )
        _append_event(
            connection,
            job_id=job_id,
            event_type=event_type,
            from_status="running",
            to_status=next_status,
            worker_id=row["lease_owner"],
            created_at=timestamp,
            detail={
                "attempts": attempts,
                "max_attempts": max_attempts,
                "available_at": available_at,
                "error": error,
            },
        )
        failed = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    assert failed is not None
    return _job_from_row(failed)


def get_research_job(path: Path, job_id: str) -> ResearchJob | None:
    initialize_research_job_queue(path)
    with _connect(path) as connection:
        row = connection.execute(
            "SELECT * FROM research_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return _job_from_row(row) if row is not None else None


def list_research_jobs(path: Path, *, limit: int = 100) -> list[ResearchJob]:
    if limit < 1:
        raise ValueError("limit must be positive")
    initialize_research_job_queue(path)
    with _connect(path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM research_jobs
            ORDER BY created_at DESC, job_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_job_from_row(row) for row in rows]


def research_job_events(path: Path, job_id: str) -> list[ResearchJobEvent]:
    initialize_research_job_queue(path)
    with _connect(path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM research_job_events
            WHERE job_id = ?
            ORDER BY event_sequence
            """,
            (job_id,),
        ).fetchall()
    return [_event_from_row(row) for row in rows]


def research_job_to_dict(job: ResearchJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "idempotency_key": job.idempotency_key,
        "status": job.status,
        "config_paths": job.config_paths,
        "output_dir": job.output_dir,
        "comparison_metric": job.comparison_metric,
        "limit": job.limit,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "available_at": job.available_at,
        "lease_owner": job.lease_owner,
        "lease_expires_at": job.lease_expires_at,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


def research_job_event_to_dict(event: ResearchJobEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "job_id": event.job_id,
        "event_type": event.event_type,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "worker_id": event.worker_id,
        "detail": event.detail,
        "created_at": event.created_at,
    }


def _connect(path: Path) -> Connection:
    connection = connect(path, timeout=30.0)
    connection.row_factory = Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def _append_event(
    connection: Connection,
    *,
    job_id: str,
    event_type: str,
    from_status: str | None,
    to_status: str,
    created_at: str,
    detail: dict[str, Any],
    worker_id: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO research_job_events (
            event_id, job_id, event_type, from_status, to_status, worker_id,
            detail_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uuid4().hex,
            job_id,
            event_type,
            from_status,
            to_status,
            worker_id,
            json.dumps(detail, sort_keys=True),
            created_at,
        ),
    )


def _job_from_row(row: Row) -> ResearchJob:
    return ResearchJob(
        job_id=str(row["job_id"]),
        idempotency_key=str(row["idempotency_key"]),
        status=str(row["status"]),
        config_paths=list(json.loads(row["config_paths_json"])),
        output_dir=str(row["output_dir"]),
        comparison_metric=str(row["comparison_metric"]),
        limit=row["result_limit"],
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        available_at=str(row["available_at"]),
        lease_owner=row["lease_owner"],
        lease_token=row["lease_token"],
        lease_expires_at=row["lease_expires_at"],
        result=json.loads(row["result_json"]) if row["result_json"] else None,
        error=json.loads(row["error_json"]) if row["error_json"] else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


def _event_from_row(row: Row) -> ResearchJobEvent:
    return ResearchJobEvent(
        event_id=str(row["event_id"]),
        job_id=str(row["job_id"]),
        event_type=str(row["event_type"]),
        from_status=row["from_status"],
        to_status=str(row["to_status"]),
        worker_id=row["worker_id"],
        detail=json.loads(row["detail_json"]),
        created_at=str(row["created_at"]),
    )


def _require_active_lease(row: Row, lease_token: str, timestamp: str) -> None:
    if (
        row["status"] != "running"
        or row["lease_token"] != lease_token
        or row["lease_expires_at"] is None
        or str(row["lease_expires_at"]) <= timestamp
    ):
        raise PermissionError("research job mutation requires the active lease")


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat(timespec="microseconds")
