# Design

## Domain Model

- API principal: sanitized API key id and role.
- Auth audit context: auth required flag, auth result, required role, sanitized
  API key id, and role.

## Application Flow

The FastAPI auth dependency records auth context on `request.state` before
returning or raising. The request logging middleware serializes that context
into its existing JSON log payload. Routes without auth dependencies default to
`auth_required=false` and `auth_result=not_required`.

## Interface Contract

Request log fields:

- `auth_required`
- `auth_result`
- `required_role`
- `api_key_id`
- `role`

Raw `X-API-Key` values are excluded.

## Data Model

No database migration. This story changes structured operational logs only.

## UI / Platform Impact

No CLI or API response shape change. Log consumers can now filter by auth
decision and sanitized actor context.

## Observability

Existing request logs gain auth fields for both successful and failed protected
requests. Public health requests record that auth was not required.

## Alternatives Considered

1. Keep logs without auth context.
2. Log raw API keys.
3. Add a durable audit table immediately.
