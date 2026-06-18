from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable as CallableABC
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Callable

from quant_research_agent.operations import (
    BatchRunResult,
    batch_result_to_dict,
    run_research_batch,
)
from quant_research_agent.research_job_queue import (
    ResearchJob,
    claim_research_job,
    complete_research_job,
    fail_research_job,
    get_research_job,
)


BatchExecutor = Callable[..., BatchRunResult]


@dataclass(frozen=True)
class ResearchWorkerResult:
    outcome: str
    job: ResearchJob | None


@dataclass(frozen=True)
class ResearchWorkerLoopSummary:
    worker_id: str
    stop_reason: str
    jobs_processed: int
    idle_cycles: int
    outcome_counts: dict[str, int]
    started_at: str
    finished_at: str


def run_research_worker_once(
    queue_path: Path,
    *,
    worker_id: str,
    lease_seconds: int = 300,
    retry_delay_seconds: int = 60,
    executor: BatchExecutor = run_research_batch,
    now: datetime | None = None,
) -> ResearchWorkerResult:
    job = claim_research_job(
        queue_path,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        now=now,
    )
    if job is None:
        return ResearchWorkerResult(outcome="idle", job=None)
    assert job.lease_token is not None
    try:
        batch = executor(
            config_paths=[Path(config_path) for config_path in job.config_paths],
            output_dir=Path(job.output_dir),
            comparison_metric=job.comparison_metric,
            limit=job.limit,
        )
    except Exception as exc:
        try:
            failed = fail_research_job(
                queue_path,
                job_id=job.job_id,
                lease_token=job.lease_token,
                error={"type": type(exc).__name__, "message": str(exc)},
                retry_delay_seconds=retry_delay_seconds,
                now=now,
            )
        except PermissionError:
            return _lease_lost_result(queue_path, job.job_id)
        return ResearchWorkerResult(outcome=failed.status, job=failed)

    payload = batch_result_to_dict(batch)
    if batch.status != "completed":
        try:
            failed = fail_research_job(
                queue_path,
                job_id=job.job_id,
                lease_token=job.lease_token,
                error={
                    "type": "BatchRunFailed",
                    "message": "research batch returned a failed status",
                    "batch": payload,
                },
                retry_delay_seconds=retry_delay_seconds,
                now=now,
            )
        except PermissionError:
            return _lease_lost_result(queue_path, job.job_id)
        return ResearchWorkerResult(outcome=failed.status, job=failed)

    try:
        completed = complete_research_job(
            queue_path,
            job_id=job.job_id,
            lease_token=job.lease_token,
            result=payload,
            now=now,
        )
    except PermissionError:
        return _lease_lost_result(queue_path, job.job_id)
    return ResearchWorkerResult(outcome="completed", job=completed)


def run_research_worker_loop(
    queue_path: Path,
    *,
    worker_id: str,
    lease_seconds: int = 300,
    retry_delay_seconds: int = 60,
    poll_seconds: float = 5.0,
    max_jobs: int | None = None,
    max_runtime_seconds: float | None = None,
    stop_when_idle: bool = False,
    executor: BatchExecutor = run_research_batch,
    now: datetime | None = None,
    stop_requested: CallableABC[[], bool] | None = None,
    sleep_fn: CallableABC[[float], None] = sleep,
    monotonic_fn: CallableABC[[], float] = monotonic,
) -> ResearchWorkerLoopSummary:
    if not worker_id.strip():
        raise ValueError("worker_id must not be blank")
    if poll_seconds < 0:
        raise ValueError("poll_seconds must not be negative")
    if max_jobs is not None and max_jobs < 1:
        raise ValueError("max_jobs must be positive when provided")
    if max_runtime_seconds is not None and max_runtime_seconds < 0:
        raise ValueError("max_runtime_seconds must not be negative")

    started = now or datetime.now(UTC)
    started_monotonic = monotonic_fn()
    jobs_processed = 0
    idle_cycles = 0
    outcome_counts: dict[str, int] = {}
    stop_reason = "stop_requested"

    while True:
        if stop_requested is not None and stop_requested():
            stop_reason = "stop_requested"
            break
        if max_jobs is not None and jobs_processed >= max_jobs:
            stop_reason = "max_jobs"
            break
        if (
            max_runtime_seconds is not None
            and monotonic_fn() - started_monotonic >= max_runtime_seconds
        ):
            stop_reason = "max_runtime"
            break

        result = run_research_worker_once(
            queue_path,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            retry_delay_seconds=retry_delay_seconds,
            executor=executor,
            now=now,
        )
        if result.outcome == "idle":
            idle_cycles += 1
            if stop_when_idle:
                stop_reason = "idle"
                break
            if poll_seconds > 0:
                sleep_fn(poll_seconds)
            continue

        jobs_processed += 1
        outcome_counts[result.outcome] = outcome_counts.get(result.outcome, 0) + 1

    finished = now or datetime.now(UTC)
    return ResearchWorkerLoopSummary(
        worker_id=worker_id,
        stop_reason=stop_reason,
        jobs_processed=jobs_processed,
        idle_cycles=idle_cycles,
        outcome_counts=outcome_counts,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )


def _lease_lost_result(queue_path: Path, job_id: str) -> ResearchWorkerResult:
    return ResearchWorkerResult(
        outcome="lease_lost",
        job=get_research_job(queue_path, job_id),
    )


def research_worker_result_to_dict(result: ResearchWorkerResult) -> dict[str, object]:
    return {
        "outcome": result.outcome,
        "job_id": result.job.job_id if result.job else None,
        "status": result.job.status if result.job else None,
        "attempts": result.job.attempts if result.job else None,
        "max_attempts": result.job.max_attempts if result.job else None,
        "result": result.job.result if result.job else None,
        "error": result.job.error if result.job else None,
    }


def research_worker_loop_summary_to_dict(
    summary: ResearchWorkerLoopSummary,
) -> dict[str, object]:
    return {
        "worker_id": summary.worker_id,
        "stop_reason": summary.stop_reason,
        "jobs_processed": summary.jobs_processed,
        "idle_cycles": summary.idle_cycles,
        "outcome_counts": summary.outcome_counts,
        "started_at": summary.started_at,
        "finished_at": summary.finished_at,
    }
