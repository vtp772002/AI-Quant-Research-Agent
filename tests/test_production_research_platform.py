from __future__ import annotations

import json
from pathlib import Path
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
    assert get_run(registry_path, "run-001") == record
    assert [item.run_id for item in list_runs(registry_path)] == ["run-001"]


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
