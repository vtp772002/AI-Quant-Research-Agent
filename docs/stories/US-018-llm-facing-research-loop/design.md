# Design

## Domain Model

- `ExperimentIdea`: strict schema for generated research ideas.
- `IdeaValidation`: validator output with errors and warnings.
- `ResearchMemory`: summary of prior registry rows.
- `ResearchCritique`: verdict, reasons, and next proposed experiment.
- `AlphaMiningResult`: generated ideas, config paths, and optional batch result.

## Application Flow

```text
base config + registry memory + objective
  -> LLMResearchAgent.generate_ideas
  -> validate ExperimentIdea objects
  -> write runnable config variants
```

```text
manifest.json
  -> metric-rule critic
  -> accept/reject verdict
  -> follow-up ExperimentIdea
```

```text
paper/blog text
  -> paper-to-alpha v2 extraction
  -> factor grammar validation
  -> unsupported concept and bias warnings
```

```text
mine-alpha
  -> generate ideas
  -> write configs
  -> optionally run batch
  -> write artifacts
```

## Interface Contract

CLI additions:

- `--generate-ideas`
- `--ideas-output-dir`
- `--objective`
- `--n`
- `--critique-run`
- `--paper-to-alpha-v2`
- `--mine-alpha`
- `--mine-output-dir`
- `--run-generated`

## Safety Boundary

The generated payload can only reference known factor names. It cannot generate
Python code, database migrations, broker instructions, or external provider
calls. Live LLM providers are out of scope for this story.
