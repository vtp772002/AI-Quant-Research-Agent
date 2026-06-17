# Design

## Domain Model

- Review queue: JSON artifact with schema `idea_review_v1`.
- Review record: idea name, status, config path, source, note, created time, and
  updated time.
- Statuses: `draft`, `approved`, `rejected`, `ran`, and `archived`.

## Application Flow

Idea generation writes configs, `ideas.json`, provider artifacts when present,
and `review_queue.json`.

Review commands:

- `--review-ideas --review-queue <path>` prints counts and records.
- `--set-idea-status <status> --idea-name <name> --review-queue <path>` updates
  a review record.
- `--run-approved-ideas --review-queue <path>` runs only approved configs and
  marks them `ran` when the batch completes.

Alpha mining with `--run-generated` creates a fresh queue and enforces the same
review gate. Because those records start as `draft`, one-shot generated runs are
blocked unless `--review-override` is explicitly provided.

## Interface Contract

Generated idea CLI output includes `review_queue_path`. The review queue is a
portable JSON artifact that can be inspected or updated without a database.

## Data Model

No database migration. Review state is stored beside generated idea artifacts.

## UI / Platform Impact

CLI-only workflow. No API or browser surface changes.

## Observability

The queue records status, note, and timestamps. Provider prompt, response, and
transcript artifacts remain separate evidence.

## Alternatives Considered

1. Execute draft generated configs by default.
2. Store review state only in the local SQLite experiment registry.
3. Treat provider transcript existence as approval.
