from __future__ import annotations

from collections.abc import Callable as CallableABC
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock, Thread
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
    renew_research_job_lease,
)


BatchExecutor = Callable[..., BatchRunResult]
LeaseRenewer = Callable[..., ResearchJob]


@dataclass(frozen=True)
class ResearchWorkerResult:
    outcome: str
    job: ResearchJob | None
    lease_renewals: int = 0
    lease_renewal_error: dict[str, str] | None = None


@dataclass(frozen=True)
class ResearchWorkerLoopSummary:
    worker_id: str
    stop_reason: str
    jobs_processed: int
    idle_cycles: int
    outcome_counts: dict[str, int]
    lease_renewals: int
    started_at: str
    finished_at: str


@dataclass(frozen=True)
class _LeaseRenewalSnapshot:
    count: int
    error: dict[str, str] | None


class _LeaseRenewalMonitor:
    def __init__(
        self,
        queue_path: Path,
        *,
        job_id: str,
        lease_token: str,
        lease_seconds: int,
        interval_seconds: float,
        lease_renewer: LeaseRenewer,
    ) -> None:
        self._queue_path = queue_path
        self._job_id = job_id
        self._lease_token = lease_token
        self._lease_seconds = lease_seconds
        self._interval_seconds = interval_seconds
        self._lease_renewer = lease_renewer
        self._stop_requested = Event()
        self._lock = Lock()
        self._count = 0
        self._error: dict[str, str] | None = None
        self._thread = Thread(
            target=self._run,
            name=f"research-job-lease-renewer-{job_id}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> _LeaseRenewalSnapshot:
        self._stop_requested.set()
        self._thread.join(timeout=max(1.0, self._interval_seconds + 1.0))
        return self.snapshot()

    def snapshot(self) -> _LeaseRenewalSnapshot:
        with self._lock:
            return _LeaseRenewalSnapshot(
                count=self._count,
                error=dict(self._error) if self._error is not None else None,
            )

    def _run(self) -> None:
        while not self._stop_requested.wait(self._interval_seconds):
            try:
                self._lease_renewer(
                    self._queue_path,
                    job_id=self._job_id,
                    lease_token=self._lease_token,
                    lease_seconds=self._lease_seconds,
                )
            except Exception as exc:  # pragma: no cover - asserted through public result state
                with self._lock:
                    if self._error is None:
                        self._error = {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        }
                self._stop_requested.set()
                return
            with self._lock:
                self._count += 1


def run_research_worker_once(
    queue_path: Path,
    *,
    worker_id: str,
    lease_seconds: int = 300,
    retry_delay_seconds: int = 60,
    auto_renew_seconds: float | None = None,
    lease_renewer: LeaseRenewer = renew_research_job_lease,
    executor: BatchExecutor = run_research_batch,
    now: datetime | None = None,
) -> ResearchWorkerResult:
    if auto_renew_seconds is not None and auto_renew_seconds <= 0:
        raise ValueError("auto_renew_seconds must be positive when provided")

    job = claim_research_job(
        queue_path,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        now=now,
    )
    if job is None:
        return ResearchWorkerResult(outcome="idle", job=None)
    assert job.lease_token is not None
    renewal_monitor = (
        _LeaseRenewalMonitor(
            queue_path,
            job_id=job.job_id,
            lease_token=job.lease_token,
            lease_seconds=lease_seconds,
            interval_seconds=auto_renew_seconds,
            lease_renewer=lease_renewer,
        )
        if auto_renew_seconds is not None
        else None
    )
    if renewal_monitor is not None:
        renewal_monitor.start()
    try:
        batch = executor(
            config_paths=[Path(config_path) for config_path in job.config_paths],
            output_dir=Path(job.output_dir),
            comparison_metric=job.comparison_metric,
            limit=job.limit,
        )
    except Exception as exc:
        renewal_snapshot = _stop_lease_renewal_monitor(renewal_monitor)
        if renewal_snapshot.error is not None:
            return _lease_lost_result(
                queue_path,
                job.job_id,
                lease_renewals=renewal_snapshot.count,
                lease_renewal_error=renewal_snapshot.error,
            )
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
            return _lease_lost_result(
                queue_path,
                job.job_id,
                lease_renewals=renewal_snapshot.count,
            )
        return ResearchWorkerResult(
            outcome=failed.status,
            job=failed,
            lease_renewals=renewal_snapshot.count,
        )

    renewal_snapshot = _stop_lease_renewal_monitor(renewal_monitor)
    if renewal_snapshot.error is not None:
        return _lease_lost_result(
            queue_path,
            job.job_id,
            lease_renewals=renewal_snapshot.count,
            lease_renewal_error=renewal_snapshot.error,
        )
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
            return _lease_lost_result(
                queue_path,
                job.job_id,
                lease_renewals=renewal_snapshot.count,
            )
        return ResearchWorkerResult(
            outcome=failed.status,
            job=failed,
            lease_renewals=renewal_snapshot.count,
        )

    try:
        completed = complete_research_job(
            queue_path,
            job_id=job.job_id,
            lease_token=job.lease_token,
            result=payload,
            now=now,
        )
    except PermissionError:
        return _lease_lost_result(
            queue_path,
            job.job_id,
            lease_renewals=renewal_snapshot.count,
        )
    return ResearchWorkerResult(
        outcome="completed",
        job=completed,
        lease_renewals=renewal_snapshot.count,
    )


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
    auto_renew_seconds: float | None = None,
    lease_renewer: LeaseRenewer = renew_research_job_lease,
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
    lease_renewals = 0
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
            auto_renew_seconds=auto_renew_seconds,
            lease_renewer=lease_renewer,
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
        lease_renewals += result.lease_renewals
        outcome_counts[result.outcome] = outcome_counts.get(result.outcome, 0) + 1

    finished = now or datetime.now(UTC)
    return ResearchWorkerLoopSummary(
        worker_id=worker_id,
        stop_reason=stop_reason,
        jobs_processed=jobs_processed,
        idle_cycles=idle_cycles,
        outcome_counts=outcome_counts,
        lease_renewals=lease_renewals,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )


def _stop_lease_renewal_monitor(
    monitor: _LeaseRenewalMonitor | None,
) -> _LeaseRenewalSnapshot:
    if monitor is None:
        return _LeaseRenewalSnapshot(count=0, error=None)
    return monitor.stop()


def _lease_lost_result(
    queue_path: Path,
    job_id: str,
    *,
    lease_renewals: int = 0,
    lease_renewal_error: dict[str, str] | None = None,
) -> ResearchWorkerResult:
    return ResearchWorkerResult(
        outcome="lease_lost",
        job=get_research_job(queue_path, job_id),
        lease_renewals=lease_renewals,
        lease_renewal_error=lease_renewal_error,
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
        "lease_renewals": result.lease_renewals,
        "lease_renewal_error": result.lease_renewal_error,
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
        "lease_renewals": summary.lease_renewals,
        "started_at": summary.started_at,
        "finished_at": summary.finished_at,
    }
