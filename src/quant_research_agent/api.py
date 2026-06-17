from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import json
import logging
import os

from quant_research_agent.config import load_config
from quant_research_agent.experiment_registry import get_run, list_runs, record_to_dict
from quant_research_agent.signals import generate_signal_as_of, signal_result_to_dict
from quant_research_agent.workflow import run_configured_workflow

try:
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - exercised only in minimal installs.
    raise RuntimeError("FastAPI service requires installing the service extra: pip install -e '.[service]'") from exc


LOGGER = logging.getLogger("quant_research_agent.api")
logging.basicConfig(level=os.getenv("AIQRA_LOG_LEVEL", "INFO"))


class RunExperimentRequest(BaseModel):
    config_path: str = "configs/base.yaml"


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
            LOGGER.info(
                json.dumps(
                    {
                        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "level": "INFO",
                        "request_id": request_id,
                        "action": f"{request.method} {request.url.path}",
                        "duration_ms": duration_ms,
                        "status_code": status_code,
                        "message": "request completed",
                    },
                    sort_keys=True,
                )
            )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics(registry_path: str | None = None) -> dict[str, object]:
        runs = list_runs(_registry_path(registry_path), limit=1000)
        return {
            "status": "ok",
            "registered_runs": len(runs),
            "latest_run_id": runs[0].run_id if runs else None,
        }

    @app.post("/experiments/run")
    def run_experiment(request: RunExperimentRequest) -> dict[str, object]:
        return run_configured_workflow(Path(request.config_path)).payload

    @app.get("/experiments")
    def experiments(registry_path: str | None = None, limit: int = 20) -> dict[str, object]:
        return {
            "runs": [record_to_dict(record) for record in list_runs(_registry_path(registry_path), limit=limit)]
        }

    @app.get("/experiments/{run_id}")
    def experiment(run_id: str, registry_path: str | None = None) -> dict[str, object]:
        record = get_run(_registry_path(registry_path), run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return record_to_dict(record)

    @app.get("/reports/{run_id}")
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

    @app.get("/signals/latest")
    def latest_signal(config_path: str = "configs/base.yaml") -> dict[str, object]:
        path = Path(config_path)
        config = load_config(path)
        return signal_result_to_dict(
            generate_signal_as_of(config=config, as_of_date=config.data.end, config_path=path)
        )

    @app.get("/signals/as-of")
    def signal_as_of(config_path: str = "configs/base.yaml", date: str | None = None) -> dict[str, object]:
        path = Path(config_path)
        config = load_config(path)
        return signal_result_to_dict(
            generate_signal_as_of(config=config, as_of_date=date or config.data.end, config_path=path)
        )

    return app


app = create_app()


def _registry_path(value: str | None = None) -> Path:
    return Path(value or os.getenv("AIQRA_EXPERIMENT_REGISTRY", "results/experiments.sqlite"))


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
