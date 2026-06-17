# Overview

## Current Behavior

The API requires keys and roles for non-health routes, and request middleware
emits structured JSON logs. Logs include request id, action, duration, and
status code, but not authenticated actor context or auth decision outcome.

## Target Behavior

Every API request log includes auth context. Public routes record that auth was
not required. Protected routes record whether auth succeeded, failed, or was
misconfigured, plus sanitized API key id, role, and required role when
available. Raw API keys are never logged.

## Affected Users

- Operator diagnosing API access.
- Quant researcher using protected API routes.
- Future developer promoting request logs into durable audit storage.

## Affected Product Docs

- `README.md`
- `docs/product/ai-quant-research-agent.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Raw API key logging.
- User identity, tenants, sessions, or JWTs.
- Tamper-proof audit storage.
- Database-backed request audit table.
