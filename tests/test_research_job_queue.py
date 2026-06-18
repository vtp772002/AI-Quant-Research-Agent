from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlite3 import connect

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
    assert shown["status"] == "completed"
    assert Path(shown["result"]["summary_path"]).exists()


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
