# Design

## Domain Model

- Prompt payload: versioned JSON request with objective, factor grammar, base
  experiment, research memory, output schema, and safety rules.
- Provider artifacts: prompt path, response path, transcript path, provider, and
  prompt version.
- Provider response: strict JSON with an `ideas` array.

## Provider Modes

- `deterministic`: default local generator, no external process.
- `fixture`: reads saved JSON, useful for reviewed transcripts and CI.
- `command`: sends prompt JSON to an external command and reads JSON from
  stdout; requires explicit allowance.

## Interface Contract

CLI flags:

- `--llm-provider deterministic|fixture|command`
- `--llm-fixture <path>`
- `--llm-command <command>`
- `--allow-external-llm`
- `--llm-prompt-version <version>`

Provider output is always converted to `ExperimentIdea` and validated before
configs are written.

## Safety Boundary

The command provider can execute an external process, so it is blocked unless
the operator passes `--allow-external-llm` or sets `AIQRA_ALLOW_EXTERNAL_LLM=1`.
The repo does not store secrets or manage vendor credentials in this story.
