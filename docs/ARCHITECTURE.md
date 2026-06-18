# Architecture

The current application stack is Python, pandas, a CLI surface, and an internal
FastAPI service surface. The first durable experiment registry is SQLite. The
repository remains a research platform, not a trading execution system.

## Discovery Before Shape

Before proposing implementation shape, identify:

- Product surfaces: browser, mobile, desktop, CLI, API, worker, or service.
- Runtime stack: language, framework, database, queues, providers, and hosting.
- Core domains: the product concepts that deserve stable names and contracts.
- Boundary inputs: user input, API requests, webhooks, jobs, files, credentials,
  provider payloads, and environment configuration.
- Validation ladder: the smallest checks that can prove the selected stack.

Record stack choices in `docs/decisions/` when they meaningfully constrain
future work.

## Current Layering

```text
quant_research_agent.config
  parse YAML and environment-shaped boundaries

quant_research_agent.data / factors / backtest
  domain and computation

quant_research_agent.agents
  application workflow components

quant_research_agent.workflow
  CLI/API orchestration boundary

quant_research_agent.locked_holdout
  fail-closed local locked-holdout manifest validation for promotion evidence

quant_research_agent.api_auth
  API key parsing, role hierarchy, FastAPI authorization dependencies, and sanitized request auth context

quant_research_agent.experiment_registry
  local durable run registry

quant_research_agent.signals
  as-of signal generation boundary

quant_research_agent.operations / registry_export
  batch run orchestration, offline registry handoff, governance manifest,
  and hash-chain verification

quant_research_agent.managed_registry
  deterministic local dry-run adapter for Postgres/object-lock registry
  deployment bundles

quant_research_agent.research_job_queue / research_job_worker
  durable local batch job state, transactional leases, retry/dead-letter
  transitions, lifecycle events, one-shot worker execution, and bounded local
  worker-loop supervision, lease renewal, heartbeat timestamps, and stale-job
  diagnostics

quant_research_agent.promotion_authorization
  two-person family-promotion recommendation, decision, frozen evidence,
  serialized append, HMAC-authenticated hash-chain verification, and summary
  queries

quant_research_agent.paper_alpha / execution_simulator
  research-template extraction and broker-free execution feasibility modeling

quant_research_agent.research_agents
  LLM-facing idea schema, strict validation, memory, critique, and alpha-mining orchestration

quant_research_agent.llm_provider
  prompt/schema versioning, provider guardrails, live OpenAI adapter,
  request/cost controls, provider eval artifacts, and prompt/response
  transcript artifacts

quant_research_agent.idea_review
  human review queue, append-only review audit ledger, idea approval state, and run gate enforcement

quant_research_agent.main / api
  app surfaces, including role-scoped review queue API orchestration
```

## Default Layering For Future Additions

```text
domain
  <- application
      <- infrastructure
          <- interface
              <- app surfaces
```

## Candidate Structure

```text
app/
  domain/
    entities/
    value-objects/
    repositories/
    services/

  application/
    commands/
    queries/
    handlers/

  infrastructure/
    database/
    logging/
    notifications/

  interface/
    controllers/
    dto/
    presenters/
    routes/
    middlewares/

surfaces/
  browser/
  mobile/
  desktop/
  cli/
```

This is a thinking template, not a scaffold. Create real folders only when a
story enters implementation and the selected stack needs them.

## Dependency Rule

Inner layers must not depend on outer layers.

| Layer | May depend on | Must not depend on |
| --- | --- | --- |
| domain | nothing project-external except tiny pure utilities | framework, database, UI, provider, process/env |
| application | domain | framework, UI, provider, database concrete clients |
| infrastructure | domain, application | interface controllers or UI |
| interface | all backend layers | UI state or platform shell assumptions |
| app surfaces | API contracts and app-facing clients | domain internals directly |

## Parse-First Boundary Rule

Unknown data must be parsed at boundaries before it enters inner code.

Boundaries include:

- HTTP request bodies, params, and query strings.
- Session payloads and identity claims.
- Environment variables.
- Database rows returned from external clients.
- Platform shell payloads.
- Deep links, tokens, and signed URLs.
- Provider webhooks, events, and async payloads.

Target flow:

```text
unknown input
  -> parser
  -> typed DTO or command
  -> application use case
  -> domain object/value object
```

Inner layers should work with meaningful product types such as `UserId`,
`AccountId`, `WorkspaceId`, `Role`, `DateRange`, or domain-specific IDs,
rather than repeatedly validating raw strings.

## Command/Query Boundary

If the product has both reads and writes, keep command/query separation clear at
the code level even when the storage layer is simple:

- Commands mutate state and own audit side effects.
- Queries read state and format for consumers.
- Shared domain rules live in domain/application, not controllers.

The review queue API follows this split: summary and audit endpoints are
queries, while status updates and approved-idea runs are commands that delegate
state changes to `idea_review` and batch execution to `operations`.

Family promotion follows the same separation. Listing and verification are
queries. Recommendation and decision are commands that delegate to
`promotion_authorization`; controllers supply authenticated actor identity and
role but do not implement promotion rules.

Research jobs follow the same command/query split. Enqueue and worker
transitions are commands owned by `research_job_queue`; list, show, and events
are queries. The worker delegates execution to `operations.run_research_batch`
and never updates queue rows directly.

Promotion actor separation uses a collision-resistant SHA-256 API-key
fingerprint distinct from the masked `api_key_id` used in operational logs.
Ledger HMAC keys come from `AIQRA_PROMOTION_LEDGER_HMAC_KEY` and must never be
written to logs or artifacts.

Live LLM provider calls stay at the provider boundary. `research_agents` consumes
validated idea payloads, not raw provider responses or credentials.

## Observability Contract

The future server should emit one canonical JSON log line per request with:

- timestamp
- level
- request_id
- user_id when known
- api_key_id when authenticated through the API key boundary
- role when authenticated through the API key boundary
- auth_required, auth_result, and required_role for API access decisions
- action
- duration_ms
- status_code
- message

Audit logs are product records. Application logs are operational records. Do not
use one as a substitute for the other.
