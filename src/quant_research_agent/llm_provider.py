from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json
import os
import subprocess
import urllib.error
import urllib.request


PROMPT_SCHEMA_VERSION = "research_idea_v1"
DEFAULT_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


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
    model: str | None = None,
    api_url: str | None = None,
    timeout_seconds: float = 60.0,
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
    elif provider == "openai":
        if not allow_external and os.getenv("AIQRA_ALLOW_EXTERNAL_LLM") != "1":
            raise PermissionError("provider=openai requires --allow-external-llm or AIQRA_ALLOW_EXTERNAL_LLM=1")
        api_key = os.getenv("AIQRA_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("provider=openai requires AIQRA_OPENAI_API_KEY or OPENAI_API_KEY")
        model_name = model or os.getenv("AIQRA_OPENAI_MODEL")
        if not model_name:
            raise ValueError("provider=openai requires --llm-model or AIQRA_OPENAI_MODEL")
        endpoint = api_url or os.getenv("AIQRA_OPENAI_RESPONSES_URL") or DEFAULT_OPENAI_RESPONSES_URL
        warnings.append("Live OpenAI provider was used; review transcript and queue before trusting generated ideas.")
        response_payload = _run_openai_responses_provider(
            prompt_payload=prompt_payload,
            api_key=api_key,
            model=model_name,
            api_url=endpoint,
            timeout_seconds=timeout_seconds,
        )
    else:
        raise ValueError("provider must be 'deterministic', 'fixture', 'command', or 'openai'")

    response_path.write_text(json.dumps(response_payload, indent=2, sort_keys=True), encoding="utf-8")
    ideas = response_payload.get("ideas")
    if not isinstance(ideas, list):
        raise ValueError("provider response must contain an ideas array")
    transcript = {
        "provider": provider,
        "prompt_path": str(prompt_path),
        "response_path": str(response_path),
        "prompt_version": prompt_payload.get("prompt_version"),
        "response_metadata": response_payload.get("provider_metadata", {}),
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


def _run_openai_responses_provider(
    *,
    prompt_payload: dict[str, Any],
    api_key: str,
    model: str,
    api_url: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    request_payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You generate quant research ideas. Return only strict JSON "
                            "matching the user's output_schema. Do not include markdown."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(prompt_payload, sort_keys=True),
                    }
                ],
            },
        ],
    }
    api_response = _post_json(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        payload=request_payload,
        timeout_seconds=timeout_seconds,
    )
    text = _extract_openai_output_text(api_response)
    parsed = _loads_json_text(text)
    ideas = parsed.get("ideas")
    if not isinstance(ideas, list):
        raise ValueError("OpenAI provider response must contain an ideas array")
    return {
        "ideas": ideas,
        "provider_metadata": {
            "provider": "openai",
            "api_url": api_url,
            "model": model,
            "response_id": api_response.get("id"),
            "status": api_response.get("status"),
            "usage": api_response.get("usage"),
        },
    }


def _post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI provider request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI provider request failed: {exc.reason}") from exc
    return json.loads(raw)


def _extract_openai_output_text(api_response: dict[str, Any]) -> str:
    direct_text = api_response.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text
    chunks: list[str] = []
    for item in api_response.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                chunks.append(str(content["text"]))
    text = "".join(chunks).strip()
    if not text:
        raise ValueError("OpenAI provider response did not contain output text")
    return text


def _loads_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("provider response JSON must be an object")
    return payload
