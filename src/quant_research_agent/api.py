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
from quant_research_agent.promotion_authorization import (
    decide_family_promotion,
    list_family_promotions,
    promotion_ledger_verification_to_dict,
    recommend_family_promotion,
    verify_promotion_ledger,
)
from quant_research_agent.research_job_queue import (
    enqueue_research_job,
    get_research_job,
    list_research_jobs,
    research_job_event_to_dict,
    research_job_events,
    research_job_to_dict,
)
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


class RecommendFamilyPromotionRequest(BaseModel):
    source_path: str
    family_id: str
    run_id: str
    ledger_path: str = "results/promotions/promotion_ledger.jsonl"
    note: str = ""
    fdr_alpha: float = 0.10


class DecideFamilyPromotionRequest(BaseModel):
    ledger_path: str = "results/promotions/promotion_ledger.jsonl"
    recommendation_id: str
    decision: str
    note: str = ""


class EnqueueResearchJobRequest(BaseModel):
    config_paths: list[str]
    output_dir: str = "results/job_batches"
    idempotency_key: str
    comparison_metric: str = "sharpe"
    limit: int | None = None
    max_attempts: int = 3
    queue_path: str = "results/research_jobs.sqlite"


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

    @app.get("/promotions")
    def family_promotions(
        family_ledger: str,
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        return _promotion_payload(
            lambda: list_family_promotions(
                Path(family_ledger),
                signing_key=_promotion_signing_key(),
            )
        )

    @app.post("/promotions/recommend")
    def recommend_promotion(
        request: RecommendFamilyPromotionRequest,
        principal: ApiPrincipal = Depends(require_role("researcher")),
    ) -> dict[str, object]:
        return _promotion_payload(
            lambda: recommend_family_promotion(
                source_path=Path(request.source_path),
                family_id=request.family_id,
                run_id=request.run_id,
                ledger_path=Path(request.ledger_path),
                actor=f"api:{principal.actor_id}",
                role=principal.role,
                signing_key=_promotion_signing_key(),
                note=request.note,
                fdr_alpha=request.fdr_alpha,
            )
        )

    @app.post("/promotions/decide")
    def decide_promotion(
        request: DecideFamilyPromotionRequest,
        principal: ApiPrincipal = Depends(require_role("operator")),
    ) -> dict[str, object]:
        return _promotion_payload(
            lambda: decide_family_promotion(
                ledger_path=Path(request.ledger_path),
                recommendation_id=request.recommendation_id,
                decision=request.decision,
                actor=f"api:{principal.actor_id}",
                role=principal.role,
                signing_key=_promotion_signing_key(),
                note=request.note,
            )
        )

    @app.get("/promotions/verify")
    def verify_promotions(
        family_ledger: str,
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        return _promotion_payload(
            lambda: promotion_ledger_verification_to_dict(
                verify_promotion_ledger(
                    Path(family_ledger),
                    signing_key=_promotion_signing_key(),
                )
            )
        )

    @app.post("/jobs/research")
    def enqueue_job(
        request: EnqueueResearchJobRequest,
        principal: ApiPrincipal = Depends(require_role("researcher")),
    ) -> dict[str, object]:
        return _job_payload(
            lambda: research_job_to_dict(
                enqueue_research_job(
                    Path(request.queue_path),
                    config_paths=[Path(path) for path in request.config_paths],
                    output_dir=Path(request.output_dir),
                    idempotency_key=request.idempotency_key,
                    comparison_metric=request.comparison_metric,
                    limit=request.limit,
                    max_attempts=request.max_attempts,
                    submitted_by=f"api:{principal.actor_id}",
                )
            )
        )

    @app.get("/jobs/research")
    def research_jobs(
        queue_path: str = "results/research_jobs.sqlite",
        limit: int = 20,
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        return _job_payload(
            lambda: {
                "jobs": [
                    research_job_to_dict(job)
                    for job in list_research_jobs(Path(queue_path), limit=limit)
                ]
            }
        )

    @app.get("/jobs/research/{job_id}")
    def research_job(
        job_id: str,
        queue_path: str = "results/research_jobs.sqlite",
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        job = _job_payload(lambda: get_research_job(Path(queue_path), job_id))
        if job is None:
            raise HTTPException(status_code=404, detail=f"research job not found: {job_id}")
        return research_job_to_dict(job)

    @app.get("/jobs/research/{job_id}/events")
    def research_job_event_log(
        job_id: str,
        queue_path: str = "results/research_jobs.sqlite",
        principal: ApiPrincipal = Depends(require_role("viewer")),
    ) -> dict[str, object]:
        _ = principal
        return _job_payload(
            lambda: {
                "job_id": job_id,
                "events": [
                    research_job_event_to_dict(event)
                    for event in research_job_events(Path(queue_path), job_id)
                ],
            }
        )

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


def _promotion_payload(loader):
    try:
        return loader()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="family promotion artifact not found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _job_payload(loader):
    try:
        return loader()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _promotion_signing_key() -> str:
    signing_key = os.getenv("AIQRA_PROMOTION_LEDGER_HMAC_KEY", "")
    if len(signing_key) < 16:
        raise HTTPException(
            status_code=503,
            detail="family promotion ledger signing is not configured",
        )
    return signing_key


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
