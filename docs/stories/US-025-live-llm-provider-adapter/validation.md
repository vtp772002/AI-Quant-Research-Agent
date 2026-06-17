# Validation

## Proof Strategy

The story is done when `openai` provider calls are blocked by default, fake
Responses API transport can produce validated ideas and review queues, artifacts
exclude raw keys, and the full offline suite remains green.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | OpenAI provider guard, request payload, output text parsing, raw-key exclusion. |
| Integration | `generate_idea_configs_with_provider(provider="openai")` writes configs, ideas, transcripts, and draft review queue using fake transport. |
| E2E | Full pytest suite remains green. |
| Platform | Compileall and diff check. |
| Performance | Not applicable. |
| Logs/Audit | Provider transcript records metadata and warning without credentials. |

## Fixtures

- Fake `_post_json` transport returning an OpenAI-like Responses payload.
- `AIQRA_OPENAI_API_KEY=sk-test-secret`.
- Explicit test model `test-model`.

## Commands

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python -m compileall -q src tests
git diff --check
```

## Acceptance Evidence

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_agents.py -q`
  passed 13/13.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` passed 44/44.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.
- CLI guard smoke with `--llm-provider openai` and no external allowance failed
  closed before any live provider request, returning
  `provider=openai requires --allow-external-llm or AIQRA_ALLOW_EXTERNAL_LLM=1`.
