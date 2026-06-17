# Human Review Gate For Generated Ideas

Date: 2026-06-17

## Status

Accepted

## Context

US-018 and US-019 created a research loop that can generate experiment configs
from deterministic, fixture, or explicitly allowed command providers. Even with
strict schema validation, generated ideas can encode weak assumptions,
overfitted factor combinations, or provider artifacts that should not be run as
research evidence without human intent.

## Decision

Add a review queue between idea generation and execution:

- Every generated idea config writes one `review_queue.json` record.
- Records use `draft`, `approved`, `rejected`, `ran`, or `archived`.
- Batch execution from generated configs requires `approved` status.
- A CLI operator can inspect the queue, update status, and run approved ideas.
- `--review-override` exists only for explicit local override and is recorded in
  the queue note after execution.

## Alternatives Considered

1. Keep relying on provider transcripts and validator output. Rejected because
   schema validity is not research approval.
2. Let `--run-generated` execute draft configs by default. Rejected because the
   safest default is no execution without explicit review.
3. Store review state only in the experiment registry. Rejected for now because
   generated ideas are artifacts before they become runs.

## Consequences

Positive:

- Generated research ideas have an explicit human approval boundary.
- Live or command-backed provider work can reuse the same gate.
- Review state is portable with the generated idea artifacts.

Tradeoffs:

- Local alpha-mining workflows need one additional approve step before running.
- The queue is artifact-backed JSON, not a multi-user audit table.

## Follow-Up

- Promote review state into a managed registry table if multi-user review,
  retention, or role-scoped approvals are added.
