# Exec Plan

## Goal

Implement the first Level 1 production research platform slice without
pretending the repo is ready for paper or live trading.

## Scope

In scope:

- Reusable workflow orchestration shared by CLI and API.
- SQLite experiment registry.
- As-of signal generation.
- Internal FastAPI service.
- Request logging middleware.
- Docker, compose, environment example, and CI workflow.
- Tests for registry, as-of signal generation, and API contract.

Out of scope:

- Live trading.
- Paper trading.
- Broker keys or broker SDKs.
- Auth, authorization, subscriptions, or customer workspaces.
- Commercial data vendor ingestion.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- External systems.
- Audit/security.
- Multi-domain.
- Weak proof.

Hard gates:

- Audit/security because production-readiness notes include secrets and audit
  requirements.
- External provider behavior because future market data, LLM, broker, and
  storage providers are explicitly discussed.

## Work Phases

1. Discovery.
2. Design.
3. Validation planning.
4. Implementation.
5. Verification.
6. Harness update.

## Stop Conditions

Pause for human confirmation if:

- A broker/live trading requirement becomes mandatory.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Auth or customer-facing SaaS behavior becomes required.
