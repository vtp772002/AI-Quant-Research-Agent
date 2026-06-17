# Validation

## Proof Strategy

The story is done when generated idea configs always write a review queue,
draft configs cannot run through generated execution without approval, approved
configs can be selected for batch execution, and the CLI can inspect and update
review state.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Review queue load, summary, status update, approved config selection, gate enforcement. |
| Integration | Idea generation writes a queue; alpha mining blocks draft generated configs. |
| E2E | CLI generates fixture-backed ideas, reviews the queue, approves one idea, and runs approved ideas. |
| Platform | Full pytest, compileall, and CLI smoke on local Python runtime. |
| Performance | Not applicable; queue size is bounded by generated idea count. |
| Logs/Audit | Review queue records note and timestamps; provider transcripts remain separate artifacts. |

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
PYTHONPATH=src python -m quant_research_agent.main --review-ideas --review-queue <tmp>/ideas/review_queue.json
PYTHONPATH=src python -m quant_research_agent.main --set-idea-status approved --idea-name fixture_quality_momentum --review-queue <tmp>/ideas/review_queue.json --review-note "Approved in smoke."
PYTHONPATH=src python -m quant_research_agent.main --run-approved-ideas --review-queue <tmp>/ideas/review_queue.json --batch-output-dir <tmp>/approved_batch
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q`
  passed 10/10.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 32/32.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- CLI smoke generated fixture-backed ideas, printed draft review state, approved
  `fixture_quality_momentum`, ran the approved config batch, and verified the
  final review counts were `ran: 1`, `draft: 0`, `approved: 0`.
