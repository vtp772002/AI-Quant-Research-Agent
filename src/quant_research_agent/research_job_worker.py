from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
