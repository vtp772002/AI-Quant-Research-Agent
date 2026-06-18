# US-027 Cross-Run Experiment-Family Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cross-run experiment-family controls so promotion evidence accounts for related runs, not only the within-run US-026 candidate family.

**Architecture:** Add optional family metadata to config, manifests, and SQLite registry rows. Create a pure `experiment_family.py` module that reads run manifests, extracts US-026 agent-signal evidence, applies Benjamini-Hochberg correction across runs in one family, and renders Markdown/JSON CLI artifacts. Keep the gate advisory and local/offline.

**Tech Stack:** Python 3.12+, dataclasses, JSON, SQLite, argparse, pytest, existing manifest/registry/report surfaces.

---

## File Map

- Modify `src/quant_research_agent/config.py`: `ExperimentFamilyConfig`, parser validation, `ExperimentConfig.family`.
- Modify `src/quant_research_agent/reproducibility.py`: write `experiment_family` into manifests.
- Modify `src/quant_research_agent/experiment_registry.py`: non-destructive migration and row fields for family metadata.
- Create `src/quant_research_agent/experiment_family.py`: family comparison model, BH correction, verdicts, renderers.
- Modify `src/quant_research_agent/main.py`: `--compare-family`, `--family-id`, `--family-fdr-alpha`.
- Modify checked-in demo configs with stable family metadata.
- Modify `src/quant_research_agent/agents/report_agent.py`: clarify run-level validity is not final family promotion.
- Add `tests/test_experiment_family.py`.
- Extend `tests/test_workflow.py`, `tests/test_production_research_platform.py`, and CLI tests.
- Add `docs/stories/US-027-cross-run-experiment-family-controls/*`.
- Add `docs/decisions/0020-cross-run-experiment-family-controls.md`.
- Update `README.md`, `docs/product/ai-quant-research-agent.md`, and `docs/TEST_MATRIX.md`.

## Task 1: Family config metadata

- [ ] Add failing tests in `tests/test_workflow.py`:
  - `parse_config` preserves optional default `family` with all fields `None`.
  - valid family metadata parses.
  - blank metadata values are rejected.
  - invalid `selection_policy` is rejected.
- [ ] Run focused RED:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_workflow.py -k "family" -q
```

- [ ] Implement in `config.py`:
  - `ExperimentFamilyConfig`
  - `ALLOWED_SELECTION_POLICIES`
  - strict optional string parsing
  - `ExperimentConfig.family`
- [ ] Run focused GREEN and commit:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_workflow.py -k "family" -q
git add src/quant_research_agent/config.py tests/test_workflow.py
git commit -m "Add experiment family configuration"
```

## Task 2: Manifest and registry persistence

- [ ] Add failing tests:
  - `tests/test_workflow.py` asserts workflow manifest contains `experiment_family`.
  - `tests/test_production_research_platform.py` asserts registry rows expose family fields.
  - a registry created before family columns migrates in place.
- [ ] Run focused RED:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_workflow.py tests/test_production_research_platform.py -k "family or registry" -q
```

- [ ] Implement:
  - write `experiment_family` in `reproducibility.py`.
  - add nullable family fields to `ExperimentRunRecord`.
  - add `ALTER TABLE ... ADD COLUMN` migration guarded by `PRAGMA table_info`.
  - map family fields in insert/update/select/dict conversion.
- [ ] Run focused GREEN and commit:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_workflow.py tests/test_production_research_platform.py -k "family or registry" -q
git add src/quant_research_agent/reproducibility.py src/quant_research_agent/experiment_registry.py tests/test_workflow.py tests/test_production_research_platform.py
git commit -m "Persist experiment family metadata"
```

## Task 3: Cross-run family evaluator

- [ ] Create failing unit tests in `tests/test_experiment_family.py`:
  - ranks/filters manifests by `family_id`.
  - extracts agent-signal p-values from US-026 `research_validity`.
  - applies Benjamini-Hochberg across runs.
  - emits `FAMILY_PROMOTE` when pre-registered run-level promote survives family alpha with comparable provenance.
  - emits `FAMILY_REJECT` on run-level reject or family q-value failure.
  - emits `FAMILY_REVIEW` for missing metadata, exploratory/manual selection, dirty code, mixed provenance, multiple pre-registered rows, or missing p-value evidence.
  - renders Markdown and JSON payloads.
- [ ] Run RED:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py -q
```

- [ ] Implement `src/quant_research_agent/experiment_family.py`:
  - dataclasses `ExperimentFamilyRow` and `ExperimentFamilyComparison`.
  - `compare_experiment_family(path, family_id=None, fdr_alpha=0.10, limit=None)`.
  - `family_comparison_to_dict`.
  - `family_comparison_to_markdown`.
  - clear alpha validation: `0.0 < fdr_alpha <= 0.25`.
- [ ] Run GREEN and commit:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py -q
git add src/quant_research_agent/experiment_family.py tests/test_experiment_family.py
git commit -m "Evaluate cross-run experiment families"
```

## Task 4: CLI integration and demo metadata

- [ ] Add failing CLI tests:
  - `main(["--compare-family", runs_dir, "--family-id", "...", "--json"])` prints JSON.
  - `--output` writes the rendered family comparison.
  - invalid family alpha exits with a clear error.
- [ ] Run RED:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py -k "cli" -q
```

- [ ] Implement CLI flags in `main.py`.
- [ ] Add `experiment.family` blocks to checked-in demo configs.
- [ ] Update report interpretation wording in `report_agent.py` so run-level `PROMOTE` does not imply final family promotion.
- [ ] Run targeted GREEN and deterministic smokes:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py tests/test_cli_e2e.py tests/test_workflow.py -q
PYTHONPATH=src .venv/bin/python -m quant_research_agent.main --compare-family results/runs --json --output /tmp/aiqra-family.json
```

- [ ] Commit:

```bash
git add src/quant_research_agent/main.py src/quant_research_agent/agents/report_agent.py configs tests
git commit -m "Expose experiment family comparison"
```

## Task 5: Docs, Harness, and regenerated artifacts

- [ ] Create high-risk story packet under `docs/stories/US-027-cross-run-experiment-family-controls/`.
- [ ] Create decision `docs/decisions/0020-cross-run-experiment-family-controls.md`.
- [ ] Update README/product/test matrix to describe family controls and remaining managed-registry limitation.
- [ ] Record Harness story and decision:

```bash
scripts/bin/harness-cli story add --id US-027 --title "Cross-run experiment family controls" --lane high-risk --verify "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q"
scripts/bin/harness-cli decision add --id 0020 --title "Cross-run experiment family controls" --doc docs/decisions/0020-cross-run-experiment-family-controls.md
```

- [ ] Run docs checks:

```bash
rg -n "FAMILY_PROMOTE|cross-run experiment-family|experiment_family|family q-value" README.md docs/product docs/stories/US-027-cross-run-experiment-family-controls docs/decisions/0020-cross-run-experiment-family-controls.md
git diff --check
```

- [ ] Commit:

```bash
git add README.md docs
git commit -m "Document US-027 family controls"
```

## Task 6: Full verification, merge, push

- [ ] Run full verification in feature worktree:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_experiment_family.py tests/test_workflow.py tests/test_production_research_platform.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
git diff --check
scripts/bin/harness-cli story verify US-027
```

- [ ] Update Harness evidence and trace.
- [ ] Merge to main locally, verify full suite on main, cleanup worktree/branch.
- [ ] Push `main` to `origin`.
