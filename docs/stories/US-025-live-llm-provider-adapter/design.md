# Design

## Domain Model

- Live provider request: model, Responses API URL, prompt payload, and timeout.
- Live provider response: normalized JSON object with `ideas` and
  `provider_metadata`.
- Provider artifacts: prompt path, response path, transcript path, prompt
  version, and warnings.

## Application Flow

`run_structured_provider(provider="openai")` checks explicit external
allowance, resolves credentials from environment, requires an explicit model,
posts the prompt payload to the Responses API, extracts output text, parses JSON,
and returns the existing `ideas` array contract.

`generate_idea_configs_with_provider` then converts each returned item into
`ExperimentIdea`, runs the validator, writes configs, and creates a draft review
queue exactly as it does for fixture and command providers.

## Interface Contract

CLI additions:

- `--llm-provider openai`
- `--llm-model <model>` or `AIQRA_OPENAI_MODEL`
- `--llm-api-url <url>` or `AIQRA_OPENAI_RESPONSES_URL`
- `--llm-timeout <seconds>`

Credential and allow flags:

- `AIQRA_OPENAI_API_KEY` or `OPENAI_API_KEY`
- `--allow-external-llm` or `AIQRA_ALLOW_EXTERNAL_LLM=1`

Errors:

- Missing external allowance raises `PermissionError`.
- Missing credentials or model raises `ValueError`.
- HTTP/network failures raise `RuntimeError` without logging request headers.
- Missing/invalid provider JSON raises `ValueError`.

## Data Model

No database migration. The adapter writes existing file artifacts under the idea
output directory.

## UI / Platform Impact

No browser/API impact. CLI users get a first-class live provider option while
offline deterministic and fixture paths remain the validation default.

## Observability

Prompt, normalized response, and transcript artifacts record provider name,
prompt version, model, response id, response status, usage metadata, and
warnings. Raw API keys are excluded from all artifacts.

## Alternatives Considered

1. Vendor SDK dependency.
2. Hard-coded default model.
3. Command-provider-only live integration.
