from __future__ import annotations

import json
from pathlib import Path
from sqlite3 import connect
from types import SimpleNamespace

from fastapi import HTTPException

from quant_research_agent.api import (
    RunApprovedIdeasRequest,
    UpdateIdeaStatusRequest,
    _request_log_payload,
    create_app,
)
from quant_research_agent.api_auth import clear_auth_cache, parse_api_keys, require_role
from quant_research_agent.config import parse_config
from quant_research_agent.experiment_registry import get_run, list_runs, record_run
from quant_research_agent.research_agents import generate_idea_configs
from quant_research_agent.signals import generate_signal_as_of, signal_result_to_dict


def test_experiment_registry_records_and_queries_run(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    manifest = _manifest(run_id="run-001", report_path=tmp_path / "report.md")

    record = record_run(registry_path, manifest)

    assert record.run_id == "run-001"
    assert record.test_sharpe == 1.25
    assert record.metrics["holdout"]["sharpe"] == 0.75
    assert record.metrics["research_validity"]["verdict"] == "REVIEW"
    assert record.experiment_family_id == "family-v1"
    assert record.hypothesis_id == "hypothesis-v1"
    assert record.candidate_id == "candidate-a"
    assert record.selection_policy == "pre_registered"
    assert get_run(registry_path, "run-001") == record
    assert [item.run_id for item in list_runs(registry_path)] == ["run-001"]


def test_experiment_registry_migrates_existing_rows_for_family_metadata(tmp_path: Path):
    registry_path = tmp_path / "experiments.sqlite"
    manifest = _manifest(run_id="run-001", report_path=tmp_path / "report.md")
    legacy = dict(manifest)
    legacy.pop("experiment_family")
    record_run(registry_path, legacy)
    with connect(registry_path) as connection:
        columns_before = {
            row[1]
            for row in connection.execute("PRAGMA table_info(experiment_runs)").fetchall()
        }
        connection.execute("ALTER TABLE experiment_runs DROP COLUMN experiment_family_id")
        connection.execute("ALTER TABLE experiment_runs DROP COLUMN hypothesis_id")
        connection.execute("ALTER TABLE experiment_runs DROP COLUMN candidate_id")
        connection.execute("ALTER TABLE experiment_runs DROP COLUMN selection_policy")
        columns_after_drop = {
            row[1]
            for row in connection.execute("PRAGMA table_info(experiment_runs)").fetchall()
        }

    assert "experiment_family_id" in columns_before
    assert "experiment_family_id" not in columns_after_drop

    migrated = record_run(registry_path, manifest)

    assert migrated.experiment_family_id == "family-v1"
    assert get_run(registry_path, "run-001").selection_policy == "pre_registered"


def test_generate_signal_as_of_uses_only_available_dates(tmp_path: Path):
    config = _config(tmp_path)

    result = generate_signal_as_of(config, as_of_date="2020-06-30")
    payload = signal_result_to_dict(result)

    assert payload["as_of_date"] == "2020-06-30"
    assert payload["signal_date"] <= "2020-06-30"
    assert payload["rows"]
    weights = [row["target_weight"] for row in payload["rows"]]
    assert any(weight > 0 for weight in weights)
    assert any(weight < 0 for weight in weights)
    assert all(row["data_timestamp"] <= "2020-06-30" for row in payload["rows"])
    assert all(row["model_version"] for row in payload["rows"])


def test_api_exposes_health_signal_and_missing_run_contract(tmp_path: Path):
    config_path = tmp_path / "service.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    registry_path = tmp_path / "registry.sqlite"
    app = create_app()

    health = _endpoint(app, "/health")()
    signal = _endpoint(app, "/signals/as-of")(
        config_path=str(config_path),
        date="2020-06-30",
    )

    assert health == {"status": "ok"}
    assert signal["signal_date"] <= "2020-06-30"
    assert signal["rows"]
    try:
        _endpoint(app, "/experiments/{run_id}")(
            run_id="missing-run",
            registry_path=str(registry_path),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "run not found" in exc.detail
    else:
        raise AssertionError("missing run should raise HTTPException")


def test_api_auth_parser_requires_valid_roles():
    assert parse_api_keys("view-key:viewer, research-key:researcher, ops-key:operator") == {
        "view-key": "viewer",
        "research-key": "researcher",
        "ops-key": "operator",
    }

    try:
        parse_api_keys("bad-key:admin")
    except ValueError as exc:
        assert "AIQRA_API_KEYS" in str(exc)
    else:
        raise AssertionError("invalid API role should fail closed")


def test_api_requires_key_for_non_health_routes(monkeypatch):
    monkeypatch.delenv("AIQRA_API_KEYS", raising=False)
    clear_auth_cache()
    viewer_dependency = require_role("viewer")

    with pytest_http_exception(503, "not configured"):
        viewer_dependency(_request())

    monkeypatch.setenv("AIQRA_API_KEYS", "viewer-secret:viewer")
    clear_auth_cache()

    with pytest_http_exception(401, "missing API key"):
        viewer_dependency(_request())
    with pytest_http_exception(401, "invalid API key"):
        viewer_dependency(_request(), "wrong")

    monkeypatch.setenv("AIQRA_API_KEYS", "broken:admin")
    clear_auth_cache()
    with pytest_http_exception(503, "misconfigured"):
        viewer_dependency(_request(), "broken")


def test_api_roles_scope_read_and_run_access(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AIQRA_API_KEYS", "viewer-secret:viewer,research-secret:researcher")
    clear_auth_cache()
    config_path = tmp_path / "service.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    app = create_app()
    signal_endpoint = _endpoint(app, "/signals/as-of")
    run_endpoint = _endpoint(app, "/experiments/run")
    viewer_dependency = require_role("viewer")
    researcher_dependency = require_role("researcher")

    assert viewer_dependency(_request(), "viewer-secret").role == "viewer"
    with pytest_http_exception(403, "requires researcher role"):
        researcher_dependency(_request(), "viewer-secret")
    assert researcher_dependency(_request(), "research-secret").role == "researcher"

    signal = signal_endpoint(config_path=str(config_path), date="2020-06-30")
    run = run_endpoint(type("Request", (), {"config_path": str(config_path)})())

    assert signal["signal_date"] <= "2020-06-30"
    assert run["experiment"] == "production_slice_signal"


def test_api_principal_actor_id_is_collision_resistant_when_masked_ids_match(monkeypatch):
    monkeypatch.setenv(
        "AIQRA_API_KEYS",
        "same1111tail:researcher,same2222tail:operator",
    )
    clear_auth_cache()

    researcher = require_role("researcher")(_request(), "same1111tail")
    operator = require_role("operator")(_request(), "same2222tail")

    assert researcher.api_key_id == operator.api_key_id == "same...tail"
    assert researcher.actor_id != operator.actor_id


def test_api_route_metadata_protects_non_health_routes():
    app = create_app()

    assert _route_dependencies(app, "/health") == 0
    assert _route_dependencies(app, "/metrics") == 1
    assert _route_dependencies(app, "/experiments/run") == 1
    assert _route_dependencies(app, "/experiments") == 1
    assert _route_dependencies(app, "/experiments/{run_id}") == 1
    assert _route_dependencies(app, "/reports/{run_id}") == 1
    assert _route_dependencies(app, "/signals/latest") == 1
    assert _route_dependencies(app, "/signals/as-of") == 1
    assert _route_total_dependencies(app, "/reviews/ideas") == 1
    assert _route_total_dependencies(app, "/reviews/audit") == 1
    assert _route_total_dependencies(app, "/reviews/ideas/status") == 1
    assert _route_total_dependencies(app, "/reviews/approved/run") == 1
    assert _route_total_dependencies(app, "/promotions") == 1
    assert _route_total_dependencies(app, "/promotions/recommend") == 1
    assert _route_total_dependencies(app, "/promotions/decide") == 1
    assert _route_total_dependencies(app, "/promotions/verify") == 1
    assert _route_total_dependencies(app, "/jobs/research") == 1
    assert _route_total_dependencies(app, "/jobs/research/stale") == 1
    assert _route_total_dependencies(app, "/jobs/research/{job_id}") == 1
    assert _route_total_dependencies(app, "/jobs/research/{job_id}/lease/renew") == 1
    assert _route_total_dependencies(app, "/jobs/research/{job_id}/events") == 1


def test_api_exposes_review_queue_summary_status_and_audit(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AIQRA_API_KEYS", "viewer-secret:viewer,research-secret:researcher")
    clear_auth_cache()
    generate_idea_configs(
        base_config_path=_base_config(tmp_path),
        output_dir=tmp_path / "ideas",
        objective="Review through API",
        count=1,
        registry_path=tmp_path / "memory.sqlite",
    )
    queue_path = tmp_path / "ideas" / "review_queue.json"
    app = create_app()
    viewer = require_role("viewer")(_request(), "viewer-secret")
    researcher = require_role("researcher")(_request(), "research-secret")

    summary = _endpoint(app, "/reviews/ideas")(review_queue=str(queue_path), principal=viewer)
    audit_before = _endpoint(app, "/reviews/audit")(review_queue=str(queue_path), principal=viewer)
    idea_name = summary["records"][0]["idea_name"]
    update_request = UpdateIdeaStatusRequest(
        review_queue=str(queue_path),
        idea_name=idea_name,
        status="approved",
        note="Approved through API.",
    )

    updated = _endpoint(app, "/reviews/ideas/status")(request=update_request, principal=researcher)
    audit_after = _endpoint(app, "/reviews/audit")(review_queue=str(queue_path), principal=viewer)

    assert summary["counts"]["draft"] == 1
    assert [event["event_type"] for event in audit_before["events"]] == ["created"]
    assert updated["records"][0]["status"] == "approved"
    assert [event["event_type"] for event in audit_after["events"]] == ["created", "status_changed"]
    assert audit_after["events"][1]["actor"] == "api:rese...cret"


def test_api_runs_approved_review_queue_configs(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AIQRA_API_KEYS", "research-secret:researcher")
    clear_auth_cache()
    generate_idea_configs(
        base_config_path=_base_config(tmp_path),
        output_dir=tmp_path / "ideas",
        objective="Run approved through API",
        count=1,
        registry_path=tmp_path / "memory.sqlite",
    )
    queue_path = tmp_path / "ideas" / "review_queue.json"
    app = create_app()
    researcher = require_role("researcher")(_request(), "research-secret")
    idea_name = _endpoint(app, "/reviews/ideas")(review_queue=str(queue_path), principal=researcher)["records"][0]["idea_name"]
    update_request = UpdateIdeaStatusRequest(
        review_queue=str(queue_path),
        idea_name=idea_name,
        status="approved",
        note="Approved for API run.",
    )
    run_request = RunApprovedIdeasRequest(
        review_queue=str(queue_path),
        batch_output_dir=str(tmp_path / "approved_batch"),
        comparison_metric="sharpe",
        limit=None,
    )

    _endpoint(app, "/reviews/ideas/status")(request=update_request, principal=researcher)
    result = _endpoint(app, "/reviews/approved/run")(request=run_request, principal=researcher)
    audit = _endpoint(app, "/reviews/audit")(review_queue=str(queue_path), principal=researcher)

    assert result["status"] == "completed"
    assert result["successful_runs"] == 1
    assert [event["event_type"] for event in audit["events"]] == ["created", "status_changed", "ran"]
    assert audit["events"][2]["actor"] == "api:rese...cret"


def test_api_enforces_two_person_family_promotion_roles(monkeypatch, tmp_path: Path):
    try:
        from quant_research_agent.api import (
            DecideFamilyPromotionRequest,
            RecommendFamilyPromotionRequest,
        )
    except ImportError:
        raise AssertionError("family promotion API contract is not implemented")

    monkeypatch.setenv(
        "AIQRA_API_KEYS",
        "viewer-secret:viewer,research-secret:researcher,operator-secret:operator",
    )
    monkeypatch.setenv(
        "AIQRA_PROMOTION_LEDGER_HMAC_KEY",
        "test-promotion-signing-key",
    )
    clear_auth_cache()
    runs_dir = tmp_path / "runs"
    _write_promotion_manifest(runs_dir / "candidate" / "manifest.json")
    ledger_path = tmp_path / "promotions" / "promotion_ledger.jsonl"
    app = create_app()
    viewer = require_role("viewer")(_request(), "viewer-secret")
    researcher = require_role("researcher")(_request(), "research-secret")
    operator = require_role("operator")(_request(), "operator-secret")

    recommendation = _endpoint(app, "/promotions/recommend")(
        request=RecommendFamilyPromotionRequest(
            source_path=str(runs_dir),
            family_id="family-a",
            run_id="candidate-run",
            ledger_path=str(ledger_path),
            note="Recommend through API.",
            fdr_alpha=0.10,
        ),
        principal=researcher,
    )
    listed = _endpoint(app, "/promotions")(
        family_ledger=str(ledger_path),
        principal=viewer,
    )
    decision = _endpoint(app, "/promotions/decide")(
        request=DecideFamilyPromotionRequest(
            ledger_path=str(ledger_path),
            recommendation_id=recommendation["recommendation_id"],
            decision="approved",
            note="Approve through API.",
        ),
        principal=operator,
    )
    verified = _endpoint(app, "/promotions/verify")(
        family_ledger=str(ledger_path),
        principal=viewer,
    )
    rendered_ledger = ledger_path.read_text(encoding="utf-8")
    ledger_events = [
        json.loads(line)
        for line in rendered_ledger.splitlines()
    ]

    assert listed["counts"]["pending"] == 1
    assert decision["status"] == "approved"
    assert verified["valid"] is True
    assert ledger_events[0]["actor"].startswith("api:")
    assert ledger_events[1]["actor"].startswith("api:")
    assert ledger_events[0]["actor"] != ledger_events[1]["actor"]
    assert "event_hmac" in ledger_events[0]
    assert "test-promotion-signing-key" not in rendered_ledger
    assert "research-secret" not in rendered_ledger
    assert "operator-secret" not in rendered_ledger


def test_api_enqueues_and_queries_durable_research_jobs(monkeypatch, tmp_path: Path):
    try:
        from quant_research_agent.api import EnqueueResearchJobRequest
    except ImportError:
        raise AssertionError("durable research job API contract is not implemented")

    monkeypatch.setenv(
        "AIQRA_API_KEYS",
        "viewer-secret:viewer,research-secret:researcher",
    )
    clear_auth_cache()
    queue_path = tmp_path / "research_jobs.sqlite"
    app = create_app()
    viewer = require_role("viewer")(_request(), "viewer-secret")
    researcher = require_role("researcher")(_request(), "research-secret")
    request = EnqueueResearchJobRequest(
        config_paths=["configs/base.yaml"],
        output_dir=str(tmp_path / "queued_batch"),
        idempotency_key="api-daily-job",
        comparison_metric="sharpe",
        limit=1,
        max_attempts=3,
        queue_path=str(queue_path),
    )

    enqueued = _endpoint(app, "/jobs/research")(
        request=request,
        principal=researcher,
    )
    duplicate = _endpoint(app, "/jobs/research")(
        request=request,
        principal=researcher,
    )
    listed = _endpoint_by_method(app, "/jobs/research", "GET")(
        queue_path=str(queue_path),
        limit=20,
        principal=viewer,
    )
    shown = _endpoint(app, "/jobs/research/{job_id}")(
        job_id=enqueued["job_id"],
        queue_path=str(queue_path),
        principal=viewer,
    )
    events = _endpoint(app, "/jobs/research/{job_id}/events")(
        job_id=enqueued["job_id"],
        queue_path=str(queue_path),
        principal=viewer,
    )

    assert duplicate["job_id"] == enqueued["job_id"]
    assert listed["jobs"][0]["job_id"] == enqueued["job_id"]
    assert shown["status"] == "queued"
    assert [event["event_type"] for event in events["events"]] == ["enqueued"]
    assert events["events"][0]["detail"]["submitted_by"] == f"api:{researcher.actor_id}"
    assert "research-secret" not in json.dumps(events, sort_keys=True)


def test_api_renews_research_job_lease_and_reports_stale_jobs(
    monkeypatch,
    tmp_path: Path,
):
    from datetime import UTC, datetime

    from quant_research_agent.api import RenewResearchJobLeaseRequest
    from quant_research_agent.research_job_queue import (
        claim_research_job,
        enqueue_research_job,
    )

    monkeypatch.setenv(
        "AIQRA_API_KEYS",
        "viewer-secret:viewer,research-secret:researcher",
    )
    clear_auth_cache()
    queue_path = tmp_path / "research_jobs.sqlite"
    app = create_app()
    viewer = require_role("viewer")(_request(), "viewer-secret")
    researcher = require_role("researcher")(_request(), "research-secret")
    active_job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "active_batch",
        idempotency_key="api-renewal",
    )
    active_claim = claim_research_job(
        queue_path,
        worker_id="api-worker",
        lease_seconds=300,
    )
    stale_anchor = datetime(2000, 1, 1, tzinfo=UTC)
    stale_job = enqueue_research_job(
        queue_path,
        config_paths=[Path("configs/base.yaml")],
        output_dir=tmp_path / "stale_batch",
        idempotency_key="api-stale",
        now=stale_anchor,
    )
    stale_claim = claim_research_job(
        queue_path,
        worker_id="stale-worker",
        lease_seconds=30,
        now=stale_anchor,
    )
    assert active_claim is not None
    assert stale_claim is not None

    renewed = _endpoint(app, "/jobs/research/{job_id}/lease/renew")(
        job_id=active_job.job_id,
        request=RenewResearchJobLeaseRequest(
            queue_path=str(queue_path),
            lease_token=str(active_claim.lease_token),
            lease_seconds=600,
        ),
        principal=researcher,
    )
    stale = _endpoint(app, "/jobs/research/stale")(
        queue_path=str(queue_path),
        stale_after_seconds=60,
        limit=20,
        principal=viewer,
    )
    rendered = json.dumps({"renewed": renewed, "stale": stale}, sort_keys=True)

    assert renewed["job_id"] == active_job.job_id
    assert renewed["status"] == "running"
    assert renewed["last_heartbeat_at"]
    assert stale["jobs"][0]["job"]["job_id"] == stale_job.job_id
    assert stale["jobs"][0]["stale_reason"] == "lease_expired"
    assert "lease_token" not in rendered
    assert "research-secret" not in rendered
    assert str(active_claim.lease_token) not in rendered
    assert str(stale_claim.lease_token) not in rendered


def test_api_request_logs_include_sanitized_auth_context(monkeypatch):
    monkeypatch.setenv("AIQRA_API_KEYS", "viewer-secret:viewer")
    clear_auth_cache()
    viewer_dependency = require_role("viewer")
    request = _request(path="/metrics")

    viewer_dependency(request, "viewer-secret")
    payload = _request_log_payload(request, request_id="req-123", duration_ms=1.5, status_code=200)
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["auth_required"] is True
    assert payload["auth_result"] == "ok"
    assert payload["required_role"] == "viewer"
    assert payload["role"] == "viewer"
    assert payload["api_key_id"] == "view...cret"
    assert "viewer-secret" not in rendered


def test_api_request_logs_auth_failure_without_raw_key(monkeypatch):
    monkeypatch.setenv("AIQRA_API_KEYS", "viewer-secret:viewer")
    clear_auth_cache()
    viewer_dependency = require_role("viewer")
    request = _request(path="/metrics")

    with pytest_http_exception(401, "invalid API key"):
        viewer_dependency(request, "wrong-secret")
    payload = _request_log_payload(request, request_id="req-124", duration_ms=1.5, status_code=401)
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["auth_required"] is True
    assert payload["auth_result"] == "invalid_key"
    assert payload["required_role"] == "viewer"
    assert payload["api_key_id"] is None
    assert payload["role"] is None
    assert "wrong-secret" not in rendered


def test_api_request_logs_public_health_as_not_required():
    payload = _request_log_payload(_request(path="/health"), request_id="req-125", duration_ms=0.5, status_code=200)

    assert payload["auth_required"] is False
    assert payload["auth_result"] == "not_required"
    assert payload["api_key_id"] is None
    assert payload["role"] is None


class pytest_http_exception:
    def __init__(self, status_code: int, detail_fragment: str):
        self.status_code = status_code
        self.detail_fragment = detail_fragment

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            raise AssertionError("expected HTTPException")
        if not issubclass(exc_type, HTTPException):
            return False
        assert exc.status_code == self.status_code
        assert self.detail_fragment in exc.detail
        return True


def _endpoint(app, path: str):
    for route in app.router.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(f"route not found: {path}")


def _endpoint_by_method(app, path: str, method: str):
    for route in app.router.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"route not found: {method} {path}")


def _request(path: str = "/metrics", method: str = "GET"):
    return SimpleNamespace(
        method=method,
        url=SimpleNamespace(path=path),
        state=SimpleNamespace(),
    )


def _route_dependencies(app, path: str) -> int:
    for route in app.router.routes:
        if getattr(route, "path", None) == path:
            return len(getattr(route, "dependencies", []))
    raise AssertionError(f"route not found: {path}")


def _route_total_dependencies(app, path: str) -> int:
    for route in app.router.routes:
        if getattr(route, "path", None) == path:
            return len(getattr(route, "dependencies", [])) + len(route.dependant.dependencies)
    raise AssertionError(f"route not found: {path}")


def _config(tmp_path: Path):
    return parse_config(_config_dict(tmp_path), base_dir=tmp_path)


def _base_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "base.yaml"
    config_path.write_text(_config_yaml(tmp_path), encoding="utf-8")
    return config_path


def _config_dict(tmp_path: Path) -> dict[str, object]:
    return {
        "data": {
            "source": "synthetic",
            "universe": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
            "start": "2020-01-01",
            "end": "2020-12-31",
            "seed": 31,
            "point_in_time_universe": False,
            "survivorship_bias_free": False,
            "corporate_actions_adjusted": False,
        },
        "experiment": {
            "name": "production_slice_signal",
            "train_fraction": 0.7,
            "signal": {
                "positive_factors": ["momentum_20d"],
                "negative_factors": ["volatility_20d"],
            },
            "backtest": {
                "holding_period": 5,
                "rebalance_days": 5,
                "quantile": 0.25,
            },
            "validation": {"walk_forward": {"window_count": 0}},
            "stress_tests": {
                "neutralization": {"enabled": False, "group_by": "sector"},
                "liquidity": {"enabled": False, "min_dollar_volume_rank": 0.0},
            },
            "shorting": {
                "borrow_fee_bps": 0.0,
                "shortable_symbols": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"],
            },
            "robustness": {
                "bootstrap_iterations": 0,
                "holding_periods": [],
                "quantiles": [],
                "cost_multipliers": [],
            },
            "capacity": {
                "notionals": [],
                "max_trade_participation": 0.10,
                "max_position_weight": 0.35,
            },
            "baselines": [],
        },
        "report": {
            "output_path": str(tmp_path / "report.md"),
            "experiments_path": str(tmp_path / "experiments.csv"),
            "registry_path": str(tmp_path / "experiments.sqlite"),
        },
    }


def _config_yaml(tmp_path: Path) -> str:
    return f"""
data:
  source: synthetic
  universe: [AAA, BBB, CCC, DDD, EEE, FFF, GGG, HHH]
  start: "2020-01-01"
  end: "2020-12-31"
  seed: 31
  point_in_time_universe: false
  survivorship_bias_free: false
  corporate_actions_adjusted: false

experiment:
  name: production_slice_signal
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


def _manifest(run_id: str, report_path: Path) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-06-17T00:00:00Z",
        "experiment": "registry_test",
        "config": {
            "path": "configs/base.yaml",
            "copied_path": "results/runs/run-001/config.yaml",
            "sha256": "abc123",
        },
        "code": {
            "commit": "deadbeef",
            "branch": "main",
            "dirty": False,
        },
        "data": {
            "source": "synthetic",
            "snapshot_dataset_id": None,
            "observed_symbols": ["AAA", "BBB"],
        },
        "artifacts": {
            "report_path": str(report_path),
            "experiments_path": str(report_path.with_name("experiments.csv")),
            "manifest_path": str(report_path.with_name("manifest.json")),
        },
        "experiment_family": {
            "family_id": "family-v1",
            "hypothesis_id": "hypothesis-v1",
            "candidate_id": "candidate-a",
            "selection_policy": "pre_registered",
        },
        "metrics": {
            "test": {
                "sharpe": 1.25,
                "total_return": 0.12,
                "ic_mean": 0.03,
                "max_drawdown": -0.08,
                "average_turnover": 1.1,
                "average_total_cost": 0.001,
            },
            "full": {
                "sharpe": 1.4,
                "total_return": 0.2,
            },
            "holdout": {
                "sharpe": 0.75,
                "total_return": 0.05,
            },
            "validation": {
                "sharpe": 1.25,
                "total_return": 0.12,
            },
            "research_validity": {
                "verdict": "REVIEW",
            },
        },
        "research_validity": {
            "verdict": "REVIEW",
        },
    }


def _write_promotion_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": "candidate-run",
                "generated_at": "2026-06-18T00:00:00Z",
                "experiment": "promotion_api_test",
                "config": {"sha256": "config-a"},
                "code": {"commit": "deadbeef", "dirty": False},
                "data": {"source": "synthetic", "snapshot_dataset_id": None},
                "experiment_family": {
                    "family_id": "family-a",
                    "hypothesis_id": "hypothesis-a",
                    "candidate_id": "candidate-a",
                    "selection_policy": "pre_registered",
                },
                "metrics": {
                    "holdout": {
                        "ic_mean": 0.05,
                        "sharpe": 1.25,
                        "total_return": 0.10,
                    },
                    "research_validity": {
                        "verdict": "PROMOTE",
                        "candidates": [
                            {
                                "name": "agent_signal",
                                "holdout_ic_mean": 0.05,
                                "holdout_sharpe": 1.25,
                                "holdout_total_return": 0.10,
                                "p_value": 0.01,
                                "q_value": 0.01,
                            }
                        ],
                    },
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
