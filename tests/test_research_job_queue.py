from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlite3 import connect
from time import monotonic, sleep

import json
import pytest


NOW = datetime(2026, 6, 19, 1, 0, tzinfo=UTC)


def test_enqueue_research_job_is_idempotent_and_records_one_event(tmp_path: Path):
    try:
        from quant_research_agent.research_job_queue import (
            enqueue_research_job,
            research_job_events,
        )
    except ModuleNotFoundError:
        pytest.fail("research job queue boundary is not implemented")

    queue_path = tmp_path / "research_jobs.sqlite"
    first = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="daily-2026-06-19",
        max_attempts=3,
        now=NOW,
    )
    duplicate = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="daily-2026-06-19",
        max_attempts=3,
        now=NOW,
    )

    assert first.job_id == duplicate.job_id
    assert first.status == "queued"
    assert first.attempts == 0
    assert [event.event_type for event in research_job_events(queue_path, first.job_id)] == [
        "enqueued"
    ]


def test_concurrent_workers_claim_one_job_once(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="claim-once",
        now=NOW,
    )

    def claim(worker_id: str):
        return claim_research_job(
            queue_path,
            worker_id=worker_id,
            lease_seconds=60,
            now=NOW,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(claim, ["worker-a", "worker-b"]))

    claimed = [item for item in claims if item is not None]
    assert len(claimed) == 1
    assert claimed[0].job_id == job.job_id
    assert claimed[0].status == "running"
    assert claimed[0].attempts == 1
    assert claimed[0].lease_owner in {"worker-a", "worker-b"}
    assert claimed[0].lease_token


def test_public_job_and_event_payloads_do_not_expose_lease_tokens(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        research_job_event_to_dict,
        research_job_events,
        research_job_to_dict,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="redact-lease-token",
        now=NOW,
    )
    claimed = claim_research_job(
        queue_path,
        worker_id="worker-a",
        now=NOW,
    )
    assert claimed is not None
    assert claimed.lease_token

    job_payload = research_job_to_dict(claimed)
    event_payloads = [
        research_job_event_to_dict(event)
        for event in research_job_events(queue_path, claimed.job_id)
    ]
    rendered = json.dumps(
        {"job": job_payload, "events": event_payloads},
        sort_keys=True,
    )

    assert "lease_token" not in job_payload
    assert all("lease_token" not in event for event in event_payloads)
    assert str(claimed.lease_token) not in rendered
    with connect(queue_path) as connection:
        event_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(research_job_events)"
            ).fetchall()
        }
        serialized_events = json.dumps(
            connection.execute(
                "SELECT * FROM research_job_events"
            ).fetchall(),
            sort_keys=True,
        )
    assert "lease_token" not in event_columns
    assert str(claimed.lease_token) not in serialized_events


def test_enqueue_rejects_unsupported_comparison_metric(tmp_path: Path):
    from quant_research_agent.research_job_queue import enqueue_research_job

    with pytest.raises(ValueError, match="unsupported comparison_metric"):
        enqueue_research_job(
            tmp_path / "research_jobs.sqlite",
            config_paths=[Path("configs/base.yaml")],
            output_dir=tmp_path / "batch",
            idempotency_key="bad-metric",
            comparison_metric="future_alpha",
            now=NOW,
        )


def test_idempotency_key_rejects_a_different_job_payload(tmp_path: Path):
    from quant_research_agent.research_job_queue import enqueue_research_job

    queue_path = tmp_path / "research_jobs.sqlite"
    enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch-a",
        idempotency_key="same-key",
        now=NOW,
    )

    with pytest.raises(ValueError, match="idempotency key is already bound to a different job payload"):
        enqueue_research_job(
            queue_path,
            config_paths=[Path("configs/other.yaml")],
            output_dir=tmp_path / "batch-b",
            idempotency_key="same-key",
            now=NOW,
        )


def test_expired_lease_is_recovered_and_stale_holder_cannot_complete(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        complete_research_job,
        enqueue_research_job,
        research_job_events,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="recover-expired",
        max_attempts=3,
        now=NOW,
    )
    first = claim_research_job(
        queue_path,
        worker_id="worker-a",
        lease_seconds=30,
        now=NOW,
    )
    assert first is not None
    recovered = claim_research_job(
        queue_path,
        worker_id="worker-b",
        lease_seconds=30,
        now=NOW + timedelta(seconds=31),
    )
    assert recovered is not None

    with pytest.raises(PermissionError, match="active lease"):
        complete_research_job(
            queue_path,
            job_id=job.job_id,
            lease_token=str(first.lease_token),
            result={"status": "completed"},
            now=NOW + timedelta(seconds=32),
        )

    completed = complete_research_job(
        queue_path,
        job_id=job.job_id,
        lease_token=str(recovered.lease_token),
        result={"status": "completed", "summary_path": "batch_summary.json"},
        now=NOW + timedelta(seconds=32),
    )

    assert recovered.attempts == 2
    assert completed.status == "completed"
    assert [event.event_type for event in research_job_events(queue_path, job.job_id)] == [
        "enqueued",
        "claimed",
        "lease_recovered",
        "claimed",
        "completed",
    ]


def test_lease_is_inactive_at_its_exact_expiry_timestamp(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        complete_research_job,
        enqueue_research_job,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="exact-expiry",
        now=NOW,
    )
    claimed = claim_research_job(
        queue_path,
        worker_id="worker-a",
        lease_seconds=30,
        now=NOW,
    )
    assert claimed is not None

    with pytest.raises(PermissionError, match="active lease"):
        complete_research_job(
            queue_path,
            job_id=job.job_id,
            lease_token=str(claimed.lease_token),
            result={"status": "completed"},
            now=NOW + timedelta(seconds=30),
        )


def test_active_worker_can_renew_lease_and_heartbeat_without_exposing_token(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        renew_research_job_lease,
        research_job_event_to_dict,
        research_job_events,
        research_job_to_dict,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="renew-active-lease",
        now=NOW,
    )
    claimed = claim_research_job(
        queue_path,
        worker_id="worker-a",
        lease_seconds=30,
        now=NOW,
    )
    assert claimed is not None
    assert claimed.lease_token

    renewed = renew_research_job_lease(
        queue_path,
        job_id=job.job_id,
        lease_token=str(claimed.lease_token),
        lease_seconds=90,
        now=NOW + timedelta(seconds=20),
    )
    events = [
        research_job_event_to_dict(event)
        for event in research_job_events(queue_path, job.job_id)
    ]
    rendered = json.dumps(
        {"job": research_job_to_dict(renewed), "events": events},
        sort_keys=True,
    )

    assert renewed.status == "running"
    assert renewed.lease_expires_at == (NOW + timedelta(seconds=110)).isoformat(timespec="microseconds")
    assert renewed.last_heartbeat_at == (NOW + timedelta(seconds=20)).isoformat(timespec="microseconds")
    assert [event["event_type"] for event in events] == [
        "enqueued",
        "claimed",
        "lease_renewed",
    ]
    assert events[-1]["worker_id"] == "worker-a"
    assert events[-1]["detail"]["lease_expires_at"] == renewed.lease_expires_at
    assert events[-1]["detail"]["last_heartbeat_at"] == renewed.last_heartbeat_at
    assert "lease_token" not in research_job_to_dict(renewed)
    assert str(claimed.lease_token) not in rendered


def test_stale_holder_cannot_renew_after_lease_recovery(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        renew_research_job_lease,
        research_job_events,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="stale-renewal",
        max_attempts=3,
        now=NOW,
    )
    first = claim_research_job(
        queue_path,
        worker_id="worker-a",
        lease_seconds=30,
        now=NOW,
    )
    assert first is not None
    recovered = claim_research_job(
        queue_path,
        worker_id="worker-b",
        lease_seconds=30,
        now=NOW + timedelta(seconds=31),
    )
    assert recovered is not None

    with pytest.raises(PermissionError, match="active lease"):
        renew_research_job_lease(
            queue_path,
            job_id=job.job_id,
            lease_token=str(first.lease_token),
            lease_seconds=60,
            now=NOW + timedelta(seconds=32),
        )

    renewed = renew_research_job_lease(
        queue_path,
        job_id=job.job_id,
        lease_token=str(recovered.lease_token),
        lease_seconds=60,
        now=NOW + timedelta(seconds=32),
    )

    assert renewed.lease_owner == "worker-b"
    assert renewed.last_heartbeat_at == (NOW + timedelta(seconds=32)).isoformat(timespec="microseconds")
    assert [event.event_type for event in research_job_events(queue_path, job.job_id)] == [
        "enqueued",
        "claimed",
        "lease_recovered",
        "claimed",
        "lease_renewed",
    ]


def test_stale_research_job_diagnostics_report_heartbeat_and_expired_leases(
    tmp_path: Path,
):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        list_stale_research_jobs,
        renew_research_job_lease,
        research_job_stale_diagnostic_to_dict,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    heartbeat_job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch-a",
        idempotency_key="heartbeat-stale",
        now=NOW,
    )
    expiring_job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch-b",
        idempotency_key="lease-expired",
        now=NOW,
    )
    heartbeat_claim = claim_research_job(
        queue_path,
        worker_id="worker-a",
        lease_seconds=300,
        now=NOW,
    )
    assert heartbeat_claim is not None
    expiring_claim = claim_research_job(
        queue_path,
        worker_id="worker-b",
        lease_seconds=30,
        now=NOW,
    )
    assert expiring_claim is not None
    renew_research_job_lease(
        queue_path,
        job_id=heartbeat_job.job_id,
        lease_token=str(heartbeat_claim.lease_token),
        lease_seconds=300,
        now=NOW + timedelta(seconds=40),
    )

    diagnostics = list_stale_research_jobs(
        queue_path,
        stale_after_seconds=30,
        now=NOW + timedelta(seconds=75),
    )
    payloads = [research_job_stale_diagnostic_to_dict(item) for item in diagnostics]
    by_job = {payload["job"]["job_id"]: payload for payload in payloads}
    rendered = json.dumps(payloads, sort_keys=True)

    assert by_job[heartbeat_job.job_id]["stale_reason"] == "heartbeat_stale"
    assert by_job[heartbeat_job.job_id]["last_heartbeat_at"] == (
        NOW + timedelta(seconds=40)
    ).isoformat(timespec="microseconds")
    assert by_job[expiring_job.job_id]["stale_reason"] == "lease_expired"
    assert "lease_token" not in rendered
    assert str(heartbeat_claim.lease_token) not in rendered
    assert str(expiring_claim.lease_token) not in rendered


def test_failure_retries_then_moves_job_to_dead_letter(tmp_path: Path):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        fail_research_job,
        research_job_events,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="retry-dead-letter",
        max_attempts=2,
        now=NOW,
    )
    first = claim_research_job(queue_path, worker_id="worker-a", now=NOW)
    assert first is not None
    retryable = fail_research_job(
        queue_path,
        job_id=job.job_id,
        lease_token=str(first.lease_token),
        error={"type": "RuntimeError", "message": "temporary"},
        retry_delay_seconds=10,
        now=NOW,
    )
    assert retryable.status == "retryable"
    assert (
        claim_research_job(
            queue_path,
            worker_id="worker-b",
            now=NOW + timedelta(seconds=9),
        )
        is None
    )
    second = claim_research_job(
        queue_path,
        worker_id="worker-b",
        now=NOW + timedelta(seconds=10),
    )
    assert second is not None
    dead_letter = fail_research_job(
        queue_path,
        job_id=job.job_id,
        lease_token=str(second.lease_token),
        error={"type": "RuntimeError", "message": "permanent"},
        retry_delay_seconds=10,
        now=NOW + timedelta(seconds=10),
    )

    assert dead_letter.status == "dead_letter"
    assert dead_letter.attempts == 2
    assert [event.event_type for event in research_job_events(queue_path, job.job_id)] == [
        "enqueued",
        "claimed",
        "retry_scheduled",
        "claimed",
        "dead_lettered",
    ]


def test_expired_final_attempt_is_dead_lettered_instead_of_staying_running(
    tmp_path: Path,
):
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        get_research_job,
        research_job_events,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="final-expired-attempt",
        max_attempts=1,
        now=NOW,
    )
    claimed = claim_research_job(
        queue_path,
        worker_id="worker-a",
        lease_seconds=30,
        now=NOW,
    )
    assert claimed is not None

    next_claim = claim_research_job(
        queue_path,
        worker_id="worker-b",
        lease_seconds=30,
        now=NOW + timedelta(seconds=31),
    )
    stored = get_research_job(queue_path, job.job_id)

    assert next_claim is None
    assert stored is not None
    assert stored.status == "dead_letter"
    assert [event.event_type for event in research_job_events(queue_path, job.job_id)] == [
        "enqueued",
        "claimed",
        "dead_lettered",
    ]


def test_worker_run_once_executes_batch_and_persists_artifact_result(tmp_path: Path):
    try:
        from quant_research_agent.research_job_worker import run_research_worker_once
    except ModuleNotFoundError:
        pytest.fail("research job worker boundary is not implemented")
    from quant_research_agent.research_job_queue import enqueue_research_job

    config_path = tmp_path / "worker.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[config_path],
        output_dir=tmp_path / "queued_batch",
        idempotency_key="worker-success",
        now=NOW,
    )

    result = run_research_worker_once(
        queue_path,
        worker_id="worker-a",
        lease_seconds=300,
        retry_delay_seconds=0,
        now=NOW,
    )

    assert result.outcome == "completed"
    assert result.job is not None
    assert result.job.job_id == job.job_id
    assert result.job.status == "completed"
    assert result.job.result is not None
    assert Path(str(result.job.result["summary_path"])).exists()
    assert Path(str(result.job.result["comparison_json_path"])).exists()


def test_worker_failure_uses_retry_and_dead_letter_transitions(tmp_path: Path):
    from quant_research_agent.research_job_queue import enqueue_research_job
    from quant_research_agent.research_job_worker import run_research_worker_once

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="worker-failure",
        max_attempts=2,
        now=NOW,
    )

    def failing_executor(**kwargs):
        raise RuntimeError("executor failed")

    first = run_research_worker_once(
        queue_path,
        worker_id="worker-a",
        retry_delay_seconds=0,
        executor=failing_executor,
        now=NOW,
    )
    second = run_research_worker_once(
        queue_path,
        worker_id="worker-b",
        retry_delay_seconds=0,
        executor=failing_executor,
        now=NOW,
    )

    assert first.outcome == "retryable"
    assert second.outcome == "dead_letter"
    assert second.job is not None
    assert second.job.job_id == job.job_id
    assert second.job.error == {
        "message": "executor failed",
        "type": "RuntimeError",
    }


def test_worker_reports_lease_lost_without_overwriting_recovered_job(tmp_path: Path):
    from quant_research_agent.operations import BatchRunResult
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        get_research_job,
    )
    from quant_research_agent.research_job_worker import run_research_worker_once

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="worker-loses-lease",
        max_attempts=3,
        now=NOW,
    )

    def recovering_executor(**kwargs):
        recovered = claim_research_job(
            queue_path,
            worker_id="worker-b",
            lease_seconds=30,
            now=NOW + timedelta(seconds=2),
        )
        assert recovered is not None
        return BatchRunResult(
            status="completed",
            runs=[],
            failures=[],
            summary_path=tmp_path / "summary.json",
            comparison_markdown_path=None,
            comparison_json_path=None,
        )

    result = run_research_worker_once(
        queue_path,
        worker_id="worker-a",
        lease_seconds=1,
        executor=recovering_executor,
        now=NOW,
    )
    stored = get_research_job(queue_path, job.job_id)

    assert result.outcome == "lease_lost"
    assert stored is not None
    assert stored.status == "running"
    assert stored.lease_owner == "worker-b"
    assert stored.attempts == 2


def test_worker_auto_renews_lease_during_long_running_executor(tmp_path: Path):
    from quant_research_agent.operations import BatchRunResult
    from quant_research_agent.research_job_queue import (
        enqueue_research_job,
        research_job_event_to_dict,
        research_job_events,
    )
    from quant_research_agent.research_job_worker import run_research_worker_once

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="worker-auto-renew",
        now=datetime.now(UTC),
    )

    def long_running_executor(**kwargs):
        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            if any(
                event.event_type == "lease_renewed"
                for event in research_job_events(queue_path, job.job_id)
            ):
                break
            sleep(0.01)
        assert any(
            event.event_type == "lease_renewed"
            for event in research_job_events(queue_path, job.job_id)
        )
        output_dir = kwargs["output_dir"]
        return BatchRunResult(
            status="completed",
            runs=[],
            failures=[],
            summary_path=output_dir / "batch_summary.json",
            comparison_markdown_path=None,
            comparison_json_path=None,
        )

    result = run_research_worker_once(
        queue_path,
        worker_id="worker-a",
        lease_seconds=60,
        retry_delay_seconds=0,
        auto_renew_seconds=0.01,
        executor=long_running_executor,
    )
    event_payloads = [
        research_job_event_to_dict(event)
        for event in research_job_events(queue_path, job.job_id)
    ]
    rendered_events = json.dumps(event_payloads, sort_keys=True)

    assert result.outcome == "completed"
    assert result.job is not None
    assert result.job.status == "completed"
    assert result.lease_renewals >= 1
    assert "lease_token" not in rendered_events


def test_worker_auto_renewal_loss_does_not_overwrite_recovered_job(tmp_path: Path):
    from quant_research_agent.operations import BatchRunResult
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
        get_research_job,
        renew_research_job_lease,
    )
    from quant_research_agent.research_job_worker import run_research_worker_once

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="worker-auto-renew-lost",
        max_attempts=3,
        now=NOW,
    )

    def recovering_renewer(path: Path, **kwargs):
        recovered = claim_research_job(
            path,
            worker_id="worker-b",
            lease_seconds=30,
            now=NOW + timedelta(seconds=2),
        )
        assert recovered is not None
        return renew_research_job_lease(
            path,
            job_id=kwargs["job_id"],
            lease_token=kwargs["lease_token"],
            lease_seconds=kwargs["lease_seconds"],
            now=NOW + timedelta(seconds=2),
        )

    def executor_that_finishes_after_recovery(**kwargs):
        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            stored = get_research_job(queue_path, job.job_id)
            if stored is not None and stored.lease_owner == "worker-b":
                break
            sleep(0.01)
        output_dir = kwargs["output_dir"]
        return BatchRunResult(
            status="completed",
            runs=[],
            failures=[],
            summary_path=output_dir / "batch_summary.json",
            comparison_markdown_path=None,
            comparison_json_path=None,
        )

    result = run_research_worker_once(
        queue_path,
        worker_id="worker-a",
        lease_seconds=1,
        retry_delay_seconds=0,
        auto_renew_seconds=0.01,
        lease_renewer=recovering_renewer,
        executor=executor_that_finishes_after_recovery,
        now=NOW,
    )
    stored = get_research_job(queue_path, job.job_id)

    assert result.outcome == "lease_lost"
    assert result.lease_renewal_error is not None
    assert stored is not None
    assert stored.status == "running"
    assert stored.lease_owner == "worker-b"
    assert stored.attempts == 2


def test_worker_rejects_non_positive_auto_renew_interval(tmp_path: Path):
    from quant_research_agent.research_job_worker import run_research_worker_once

    with pytest.raises(ValueError, match="auto_renew_seconds must be positive"):
        run_research_worker_once(
            tmp_path / "research_jobs.sqlite",
            worker_id="worker-a",
            auto_renew_seconds=0,
        )


def test_worker_loop_processes_jobs_until_idle_and_returns_summary(tmp_path: Path):
    from quant_research_agent.operations import BatchRunResult
    from quant_research_agent.research_job_queue import (
        enqueue_research_job,
        get_research_job,
    )
    from quant_research_agent.research_job_worker import run_research_worker_loop

    queue_path = tmp_path / "research_jobs.sqlite"
    jobs = [
        enqueue_research_job(
            queue_path,
            config_paths=[Path(f"configs/loop-{index}.yaml")],
            output_dir=tmp_path / f"batch-{index}",
            idempotency_key=f"loop-job-{index}",
            now=NOW,
        )
        for index in range(2)
    ]
    calls: list[list[Path]] = []

    def successful_executor(**kwargs):
        calls.append(kwargs["config_paths"])
        output_dir = kwargs["output_dir"]
        return BatchRunResult(
            status="completed",
            runs=[],
            failures=[],
            summary_path=output_dir / "batch_summary.json",
            comparison_markdown_path=None,
            comparison_json_path=None,
        )

    summary = run_research_worker_loop(
        queue_path,
        worker_id="loop-worker",
        stop_when_idle=True,
        poll_seconds=0,
        executor=successful_executor,
        now=NOW,
    )

    assert summary.stop_reason == "idle"
    assert summary.jobs_processed == 2
    assert summary.outcome_counts == {"completed": 2}
    assert summary.idle_cycles == 1
    assert summary.worker_id == "loop-worker"
    assert [call[0].name for call in calls] == ["loop-0.yaml", "loop-1.yaml"]
    assert [get_research_job(queue_path, job.job_id).status for job in jobs] == [
        "completed",
        "completed",
    ]


def test_worker_loop_respects_max_jobs_and_runtime_budget(tmp_path: Path):
    from quant_research_agent.operations import BatchRunResult
    from quant_research_agent.research_job_queue import (
        enqueue_research_job,
        get_research_job,
    )
    from quant_research_agent.research_job_worker import run_research_worker_loop

    queue_path = tmp_path / "research_jobs.sqlite"
    jobs = []
    for index in range(3):
        jobs.append(
            enqueue_research_job(
                queue_path,
                config_paths=[Path(f"configs/budget-{index}.yaml")],
                output_dir=tmp_path / f"batch-{index}",
                idempotency_key=f"budget-job-{index}",
                now=NOW,
            )
        )

    def successful_executor(**kwargs):
        output_dir = kwargs["output_dir"]
        return BatchRunResult(
            status="completed",
            runs=[],
            failures=[],
            summary_path=output_dir / "batch_summary.json",
            comparison_markdown_path=None,
            comparison_json_path=None,
        )

    max_jobs_summary = run_research_worker_loop(
        queue_path,
        worker_id="loop-worker",
        max_jobs=2,
        poll_seconds=0,
        executor=successful_executor,
        now=NOW,
    )
    runtime_summary = run_research_worker_loop(
        queue_path,
        worker_id="loop-worker",
        max_runtime_seconds=0,
        poll_seconds=0,
        executor=successful_executor,
        now=NOW,
    )

    assert max_jobs_summary.stop_reason == "max_jobs"
    assert max_jobs_summary.jobs_processed == 2
    assert runtime_summary.stop_reason == "max_runtime"
    assert runtime_summary.jobs_processed == 0
    assert [get_research_job(queue_path, job.job_id).status for job in jobs] == [
        "completed",
        "completed",
        "queued",
    ]


def test_research_job_cli_enqueue_list_worker_and_show(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    from quant_research_agent.main import main

    config_path = tmp_path / "cli-worker.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    queue_path = tmp_path / "research_jobs.sqlite"
    output_dir = tmp_path / "cli_batch"

    enqueue_code = main(
        [
            "--enqueue-research-job",
            str(config_path),
            "--job-queue-path",
            str(queue_path),
            "--job-idempotency-key",
            "cli-worker-job",
            "--job-output-dir",
            str(output_dir),
        ]
    )
    enqueued = json.loads(capsys.readouterr().out)
    list_code = main(
        [
            "--list-research-jobs",
            "--job-queue-path",
            str(queue_path),
        ]
    )
    listed = json.loads(capsys.readouterr().out)
    worker_code = main(
        [
            "--research-worker-run-once",
            "--job-queue-path",
            str(queue_path),
            "--worker-id",
            "cli-worker",
            "--worker-retry-delay-seconds",
            "0",
            "--worker-auto-renew-seconds",
            "0.01",
        ]
    )
    worker = json.loads(capsys.readouterr().out)
    show_code = main(
        [
            "--show-research-job",
            enqueued["job_id"],
            "--job-queue-path",
            str(queue_path),
        ]
    )
    shown = json.loads(capsys.readouterr().out)

    assert enqueue_code == list_code == worker_code == show_code == 0
    assert enqueued["status"] == "queued"
    assert listed["jobs"][0]["job_id"] == enqueued["job_id"]
    assert worker["outcome"] == "completed"
    assert "lease_renewals" in worker
    assert shown["status"] == "completed"
    assert Path(shown["result"]["summary_path"]).exists()


def test_research_job_cli_worker_loop_returns_supervision_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    from quant_research_agent.main import main

    config_path = tmp_path / "cli-loop-worker.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    queue_path = tmp_path / "research_jobs.sqlite"
    output_dir = tmp_path / "cli_loop_batch"

    assert main(
        [
            "--enqueue-research-job",
            str(config_path),
            "--job-queue-path",
            str(queue_path),
            "--job-idempotency-key",
            "cli-loop-worker-job",
            "--job-output-dir",
            str(output_dir),
        ]
    ) == 0
    capsys.readouterr()

    code = main(
        [
            "--research-worker-loop",
            "--job-queue-path",
            str(queue_path),
            "--worker-id",
            "cli-loop-worker",
            "--worker-stop-when-idle",
            "--worker-poll-seconds",
            "0",
            "--worker-retry-delay-seconds",
            "0",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["worker_id"] == "cli-loop-worker"
    assert payload["stop_reason"] == "idle"
    assert payload["jobs_processed"] == 1
    assert payload["outcome_counts"] == {"completed": 1}
    assert payload["idle_cycles"] == 1


def test_research_job_cli_renews_active_lease_without_printing_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    from quant_research_agent.main import main
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
    )

    queue_path = tmp_path / "research_jobs.sqlite"
    job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "batch",
        idempotency_key="cli-renewal",
        now=NOW,
    )
    claimed = claim_research_job(
        queue_path,
        worker_id="cli-worker",
        lease_seconds=300,
        now=NOW,
    )
    assert claimed is not None
    assert claimed.lease_token

    code = main(
        [
            "--renew-research-job-lease",
            job.job_id,
            "--job-queue-path",
            str(queue_path),
            "--job-lease-token",
            str(claimed.lease_token),
            "--worker-lease-seconds",
            "600",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    rendered = json.dumps(payload, sort_keys=True)

    assert code == 0
    assert payload["status"] == "running"
    assert payload["last_heartbeat_at"]
    assert "lease_token" not in rendered
    assert str(claimed.lease_token) not in rendered


def _config_yaml(tmp_path: Path) -> str:
    return f"""
data:
  source: synthetic
  universe: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  start: "2020-01-01"
  end: "2020-12-31"
  seed: 41
  point_in_time_universe: false
  survivorship_bias_free: false
  corporate_actions_adjusted: false

experiment:
  name: queued_worker_signal
  train_fraction: 0.7
  signal:
    positive_factors: [momentum_20d]
    negative_factors: [volatility_20d]
  backtest:
    holding_period: 5
    rebalance_days: 5
    quantile: 0.25
  validation:
    walk_forward:
      window_count: 0
  stress_tests:
    neutralization:
      enabled: false
      group_by: sector
    liquidity:
      enabled: false
      min_dollar_volume_rank: 0.0
  shorting:
    borrow_fee_bps: 0.0
    shortable_symbols: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  robustness:
    bootstrap_iterations: 0
    holding_periods: []
    quantiles: []
    cost_multipliers: []
  capacity:
    notionals: []
    max_trade_participation: 0.10
    max_position_weight: 0.35
  baselines: []

report:
  output_path: "{tmp_path / 'report.md'}"
  experiments_path: "{tmp_path / 'experiments.csv'}"
  registry_path: "{tmp_path / 'experiments.sqlite'}"
"""
