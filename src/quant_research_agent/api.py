from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import json
import logging
import os

try:
    from fastapi import Depends, FastAPI, HTTPException, Request
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - exercised only in minimal installs.
    raise RuntimeError("FastAPI service requires installing the service extra: pip install -e '.[service]'") from exc

from quant_research_agent.api_auth import ApiPrincipal, request_auth_audit, require_role
from quant_research_agent.config import load_config
from quant_research_agent.experiment_registry import get_run, list_runs, record_to_dict
from quant_research_agent.idea_review import (
    approved_config_paths,
    mark_configs_ran,
    review_audit_events,
    review_summary,
    update_idea_status,
)
from quant_research_agent.operations import batch_result_to_dict, run_research_batch
from quant_research_agent.signals import generate_signal_as_of, signal_result_to_dict
from quant_research_agent.workflow import run_configured_workflow


LOGGER = logging.getLogger("quant_research_agent.api")
logging.basicConfig(level=os.getenv("AIQRA_LOG_LEVEL", "INFO"))


class RunExperimentRequest(BaseModel):
    config_path: str = "configs/base.yaml"


class UpdateIdeaStatusRequest(BaseModel):
    review_queue: str
    idea_name: str
    status: str
    note: str = ""


class RunApprovedIdeasRequest(BaseModel):
    review_queue: str
    batch_output_dir: str = "results/idea_batches"
    comparison_metric: str = "sharpe"
    limit: int | None = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Quant Research Agent",
        version="0.1.0",
        description="Internal research-platform API for experiments, reports, and as-of signals.",
    )

    @app.middleware("http")
    async def request_log_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid4().hex)
        start = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            duration_ms = round((perf_counter() - start) * 1000.0, 3)
            LOGGER.info(json.dumps(_request_log_payload(request, request_id, duration_ms, status_code), sort_keys=True))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    viewer_required = Depends(require_role("viewer"))
    researcher_required = Depends(require_role("researcher"))

    @app.get("/metrics", dependencies=[viewer_required])
    def metrics(registry_path: str | None = None) -> dict[str, object]:
        runs = list_runs(_registry_path(registry_path), limit=1000)
        return {
            "status": "ok",
            "registered_runs": len(runs),
            "latest_run_id": runs[0].run_id if runs else None,
        }

    @app.post("/experiments/run", dependencies=[researcher_required])
    def run_experiment(request: RunExperimentRequest) -> dict[str, object]:
        return run_configured_workflow(Path(request.config_path)).payload

    @app.get("/experiments", dependencies=[viewer_required])
    def experiments(registry_path: str | None = None, limit: int = 20) -> dict[str, object]:
        return {
            "runs": [record_to_dict(record) for record in list_runs(_registry_path(registry_path), limit=limit)]
        }

    @app.get("/experiments/{run_id}", dependencies=[viewer_required])
    def experiment(run_id: str, registry_path: str | None = None) -> dict[str, object]:
        record = get_run(_registry_path(registry_path), run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return record_to_dict(record)

    @app.get("/reports/{run_id}", dependencies=[viewer_required])
    def report(run_id: str, registry_path: str | None = None) -> dict[str, object]:
        record = get_run(_registry_path(registry_path), run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        report_path = Path(record.report_path)
        if not report_path.exists():
            raise HTTPException(status_code=404, detail=f"report file not found for run: {run_id}")
        return {
            "run_id": run_id,
            "report_path": str(report_path),
            "report_markdown": report_path.read_text(encoding="utf-8"),
        }

    @app.get("/signals/latest", dependencies=[viewer_required])
    def latest_signal(config_path: str = "configs/base.yaml") -> dict[str, object]:
        path = Path(config_path)
        config = load_config(path)
        return signal_result_to_dict(
            generate_signal_as_of(config=config, as_of_date=config.data.end, config_path=path)
        )

    @app.get("/signals/as-of", dependencies=[viewer_required])
    def signal_as_of(config_path: str = "configs/base.yaml", date: str | None = None) -> dict[str, object]:
        path = Path(config_path)
        config = load_config(path)
        return signal_result_to_dict(
            generate_signal_as_of(config=config, as_of_date=date or config.data.end, config_path=path)
        )

    @app.get("/reviews/ideas")
    def idea_review_summary(
        review_queue: str,
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        return _review_payload(lambda: review_summary(Path(review_queue)))

    @app.get("/reviews/audit")
    def idea_review_audit(
        review_queue: str,
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        return _review_payload(lambda: {"queue_path": review_queue, "events": review_audit_events(Path(review_queue))})

    @app.post("/reviews/ideas/status")
    def set_idea_review_status(
        request: UpdateIdeaStatusRequest,
        principal: ApiPrincipal = Depends(require_role("researcher")),
    ) -> dict[str, object]:
        return _review_payload(
            lambda: update_idea_status(
                Path(request.review_queue),
                idea_name=request.idea_name,
                status=request.status,
                note=request.note,
                actor=f"api:{principal.api_key_id}",
            )
        )

    @app.post("/reviews/approved/run")
    def run_approved_ideas(
        request: RunApprovedIdeasRequest,
        principal: ApiPrincipal = Depends(require_role("researcher")),
    ) -> dict[str, object]:
        config_paths = _review_payload(lambda: approved_config_paths(Path(request.review_queue)))
        if not config_paths:
            raise HTTPException(status_code=400, detail="review queue has no approved ideas to run")
        try:
            result = run_research_batch(
                config_paths=config_paths,
                output_dir=Path(request.batch_output_dir),
                comparison_metric=request.comparison_metric,
                limit=request.limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if result.status == "completed":
            mark_configs_ran(Path(request.review_queue), config_paths, actor=f"api:{principal.api_key_id}")
        return batch_result_to_dict(result)

    return app


app = create_app()


def _registry_path(value: str | None = None) -> Path:
    return Path(value or os.getenv("AIQRA_EXPERIMENT_REGISTRY", "results/experiments.sqlite"))


def _review_payload(loader):
    try:
        return loader()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="review queue not found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _request_log_payload(request: Request, request_id: str, duration_ms: float, status_code: int) -> dict[str, object]:
    return {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": "INFO",
        "request_id": request_id,
        "action": f"{request.method} {request.url.path}",
        "duration_ms": duration_ms,
        "status_code": status_code,
        "message": "request completed",
        **request_auth_audit(request),
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "quant_research_agent.api:app",
        host=os.getenv("AIQRA_HOST", "0.0.0.0"),
        port=int(os.getenv("AIQRA_PORT", "8000")),
        reload=os.getenv("AIQRA_RELOAD", "0") == "1",
    )


if __name__ == "__main__":
    main()
