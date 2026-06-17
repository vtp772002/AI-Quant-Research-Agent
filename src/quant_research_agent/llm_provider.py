from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json
import os
import subprocess


PROMPT_SCHEMA_VERSION = "research_idea_v1"


@dataclass(frozen=True)
class ProviderArtifacts:
    provider: str
    prompt_version: str
    prompt_path: Path
    response_path: Path
    transcript_path: Path
    warnings: list[str]


def build_research_prompt_payload(
    *,
    objective: str,
    count: int,
    factor_names: list[str],
    memory: dict[str, Any],
    base_experiment: dict[str, Any],
    prompt_version: str = PROMPT_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "prompt_version": prompt_version,
        "task": "generate_quant_research_ideas",
        "objective": objective,
        "count": count,
        "allowed_factors": factor_names,
        "base_experiment": base_experiment,
        "research_memory": memory,
        "output_schema": {
            "ideas": [
                {
                    "name": "lowercase_snake_case",
                    "hypothesis": "string",
                    "positive_factors": ["factor_name"],
                    "negative_factors": ["factor_name"],
                    "holding_period": "integer 1..252",
                    "quantile": "float 0..0.5 exclusive",
                    "rationale": "string",
                    "confidence": "float 0..1",
                    "warnings": ["string"],
                }
            ]
        },
        "safety_rules": [
            "Only use allowed_factors.",
            "Do not emit code.",
            "Do not request credentials or external data.",
            "Return strict JSON matching output_schema.",
        ],
    }


def run_structured_provider(
    *,
    provider: str,
    prompt_payload: dict[str, Any],
    transcript_dir: Path,
    fixture_path: Path | None = None,
    command: str | None = None,
    allow_external: bool = False,
) -> tuple[list[dict[str, Any]], ProviderArtifacts]:
    transcript_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    prompt_path = transcript_dir / f"{stamp}-{provider}-prompt.json"
    response_path = transcript_dir / f"{stamp}-{provider}-response.json"
    transcript_path = transcript_dir / f"{stamp}-{provider}-transcript.json"
    prompt_path.write_text(json.dumps(prompt_payload, indent=2, sort_keys=True), encoding="utf-8")

    warnings: list[str] = []
    if provider == "fixture":
        if fixture_path is None:
            raise ValueError("fixture_path is required for provider=fixture")
        response_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    elif provider == "command":
        if not allow_external and os.getenv("AIQRA_ALLOW_EXTERNAL_LLM") != "1":
            raise PermissionError("provider=command requires --allow-external-llm or AIQRA_ALLOW_EXTERNAL_LLM=1")
        if not command:
            command = os.getenv("AIQRA_LLM_COMMAND")
        if not command:
            raise ValueError("provider=command requires --llm-command or AIQRA_LLM_COMMAND")
        warnings.append("External command provider was used; review transcript before trusting generated ideas.")
        completed = subprocess.run(
            command,
            input=json.dumps(prompt_payload),
            text=True,
            shell=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"LLM command failed with exit {completed.returncode}: {completed.stderr.strip()}")
        response_payload = json.loads(completed.stdout)
    else:
        raise ValueError("provider must be 'deterministic', 'fixture', or 'command'")

    response_path.write_text(json.dumps(response_payload, indent=2, sort_keys=True), encoding="utf-8")
    ideas = response_payload.get("ideas")
    if not isinstance(ideas, list):
        raise ValueError("provider response must contain an ideas array")
    transcript = {
        "provider": provider,
        "prompt_path": str(prompt_path),
        "response_path": str(response_path),
        "prompt_version": prompt_payload.get("prompt_version"),
        "warnings": warnings,
    }
    transcript_path.write_text(json.dumps(transcript, indent=2, sort_keys=True), encoding="utf-8")
    return ideas, ProviderArtifacts(
        provider=provider,
        prompt_version=str(prompt_payload.get("prompt_version")),
        prompt_path=prompt_path,
        response_path=response_path,
        transcript_path=transcript_path,
        warnings=warnings,
    )
