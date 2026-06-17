# Validation

## Proof Strategy

The story is done when generated idea queues create audit ledgers, status
changes and run marking append ordered events, CLI can print the audit ledger,
and existing review gate behavior remains intact.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Audit ledger path, created events, status_changed events, ran events, actor fields. |
| Integration | Idea generation writes queue and audit ledger; review summary exposes audit path. |
| E2E | CLI generate, review, approve with actor, print audit, run approved with actor, print final audit. |
| Platform | Full pytest, compileall, and diff check. |
| Performance | Not applicable; event count is bounded by review operations. |
| Logs/Audit | JSONL ledger contains ordered event history with actor, note, and status transition. |

## Fixtures

- Synthetic base config from `configs/base.yaml`.
- Fixture provider JSON with one valid idea.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
PYTHONPATH=src python -m quant_research_agent.main --generate-ideas --config configs/base.yaml --llm-provider fixture --llm-fixture <tmp>/fixture.json --ideas-output-dir <tmp>/ideas
PYTHONPATH=src python -m quant_research_agent.main --set-idea-status approved --idea-name fixture_quality_momentum --review-queue <tmp>/ideas/review_queue.json --review-note "Approved in smoke." --review-actor smoke-reviewer
PYTHONPATH=src python -m quant_research_agent.main --review-audit --review-queue <tmp>/ideas/review_queue.json
PYTHONPATH=src python -m quant_research_agent.main --run-approved-ideas --review-queue <tmp>/ideas/review_queue.json --batch-output-dir <tmp>/approved_batch --review-actor smoke-runner
PYTHONPATH=src python -m quant_research_agent.main --review-audit --review-queue <tmp>/ideas/review_queue.json
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q`
  passed 10/10.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 32/32.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- CLI smoke generated fixture-backed ideas, approved
  `fixture_quality_momentum` with actor `smoke-reviewer`, printed audit events,
  ran the approved config with actor `smoke-runner`, and verified final event
  order `created`, `status_changed`, `ran`.
