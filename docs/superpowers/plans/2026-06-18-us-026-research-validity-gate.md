# US-026 Research Validity Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an advisory, reproducible `PROMOTE`/`REVIEW`/`REJECT` research-validity gate based on an untouched chronological holdout, Benjamini-Hochberg false-discovery control, and explicit economic and data-readiness checks.

**Architecture:** Extend every backtest with a train/validation/holdout split while retaining `test` as a compatibility alias for validation. A new pure `agents/research_validity.py` module builds the evaluated candidate family, applies statistical correction, and emits named checks plus a verdict; existing report, workflow, manifest, registry, and CSV surfaces serialize that result without changing process exit status.

**Tech Stack:** Python 3.12+, dataclasses, pandas, NumPy, standard-library `math.erfc`, PyYAML, pytest, existing Markdown/JSON/CSV/SQLite artifact surfaces.

---

## File Map

- Create `src/quant_research_agent/agents/research_validity.py`: statistical correction, candidate evidence, checks, and verdict.
- Create `tests/test_research_validity.py`: focused unit tests for p-values, FDR, and all verdict branches.
- Modify `src/quant_research_agent/config.py`: validity configuration types, defaults, and validation.
- Modify `src/quant_research_agent/backtest/engine.py`: chronological holdout boundary and split metrics.
- Modify `src/quant_research_agent/agents/robustness.py`: retain completed variant backtests for holdout evidence.
- Modify `src/quant_research_agent/agents/evaluator_agent.py`: evaluate validity after all candidates are complete.
- Modify `src/quant_research_agent/agents/report_agent.py`: render and persist validity evidence.
- Modify `src/quant_research_agent/workflow.py`: add validity to CLI/API payload.
- Modify `src/quant_research_agent/reproducibility.py`: add validity and holdout metrics to manifests.
- Modify `configs/*.yaml`: explicitly enable the gate in checked-in research demos.
- Modify `tests/test_workflow.py`, `tests/test_cli_e2e.py`, and relevant focused tests: integration and artifact consistency.
- Create `docs/stories/US-026-research-validity-promotion-gate/`: high-risk story packet.
- Create `docs/decisions/0019-research-validity-promotion-gate.md`: durable methodology decision.
- Modify `README.md`, `docs/product/ai-quant-research-agent.md`, and `docs/TEST_MATRIX.md`: product contract and proof.

### Task 1: Add and validate research-validity configuration

**Files:**
- Modify: `src/quant_research_agent/config.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write failing configuration tests**

Add focused tests before production changes:

```python
import pytest

from quant_research_agent.config import parse_config


def test_parse_config_supports_research_validity(base_config_dict):
    raw = base_config_dict()
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        "holdout_fraction": 0.15,
        "fdr_alpha": 0.10,
        "min_holdout_sharpe": 0.0,
        "min_holdout_ic": 0.0,
        "require_positive_return": True,
        "require_baseline_outperformance": True,
        "require_walk_forward_stability": True,
        "require_data_readiness": True,
    }

    config = parse_config(raw)

    validity = config.experiment.validation.research_validity
    assert validity.enabled
    assert validity.holdout_fraction == 0.15
    assert validity.fdr_alpha == 0.10


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("holdout_fraction", 0.01, "holdout_fraction must be between 0.05 and 0.40"),
        ("holdout_fraction", 0.45, "holdout_fraction must be between 0.05 and 0.40"),
        ("fdr_alpha", 0.0, "fdr_alpha must be greater than 0 and at most 0.25"),
        ("fdr_alpha", 0.30, "fdr_alpha must be greater than 0 and at most 0.25"),
    ],
)
def test_parse_config_rejects_invalid_research_validity(base_config_dict, field, value, message):
    raw = base_config_dict()
    raw["experiment"]["validation"]["research_validity"] = {"enabled": True, field: value}

    with pytest.raises(ValueError, match=message):
        parse_config(raw)


def test_parse_config_preserves_validation_observations(base_config_dict):
    raw = base_config_dict()
    raw["experiment"]["train_fraction"] = 0.8
    raw["experiment"]["validation"]["research_validity"] = {
        "enabled": True,
        "holdout_fraction": 0.15,
    }

    with pytest.raises(
        ValueError,
        match="train_fraction plus research_validity.holdout_fraction must be at most 0.90",
    ):
        parse_config(raw)
```

If `tests/test_workflow.py` has no reusable config builder, extract its existing
dictionary into a local `base_config_dict()` fixture without changing behavior.

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_workflow.py -k "research_validity or preserves_validation" -q
```

Expected: collection or assertion failures because
`ValidationConfig.research_validity` does not exist.

- [ ] **Step 3: Implement configuration types and parser**

Add to `config.py`:

```python
@dataclass(frozen=True)
class ResearchValidityConfig:
    enabled: bool = False
    holdout_fraction: float = 0.15
    fdr_alpha: float = 0.10
    min_holdout_sharpe: float = 0.0
    min_holdout_ic: float = 0.0
    require_positive_return: bool = True
    require_baseline_outperformance: bool = True
    require_walk_forward_stability: bool = True
    require_data_readiness: bool = True


@dataclass(frozen=True)
class ValidationConfig:
    walk_forward: WalkForwardConfig
    research_validity: ResearchValidityConfig
```

Parse `validation.get("research_validity", {})`, convert numeric fields with
`float`, reject non-finite thresholds with `math.isfinite`, and enforce:

```python
if not 0.05 <= holdout_fraction <= 0.40:
    raise ValueError(
        "experiment.validation.research_validity.holdout_fraction must be between 0.05 and 0.40"
    )
if not 0.0 < fdr_alpha <= 0.25:
    raise ValueError(
        "experiment.validation.research_validity.fdr_alpha must be greater than 0 and at most 0.25"
    )
if train_fraction + holdout_fraction > 0.90:
    raise ValueError(
        "experiment.train_fraction plus research_validity.holdout_fraction must be at most 0.90"
    )
```

Instantiate `ResearchValidityConfig` under `ValidationConfig`.

- [ ] **Step 4: Run focused and config-adjacent tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_workflow.py tests/test_production_research_platform.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant_research_agent/config.py tests/test_workflow.py
git commit -m "Add research validity configuration"
```

### Task 2: Add train/validation/holdout backtest metrics

**Files:**
- Modify: `src/quant_research_agent/backtest/engine.py`
- Modify: `src/quant_research_agent/agents/baseline_agent.py`
- Modify: `src/quant_research_agent/agents/stress_tests.py`
- Modify: `src/quant_research_agent/agents/robustness.py`
- Modify: `src/quant_research_agent/agents/capacity.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write a failing split-isolation test**

Add a deterministic test using a small generated market panel and signal:

```python
def test_backtest_reserves_disjoint_holdout_without_changing_validation_metrics():
    market_data, signal = deterministic_market_and_signal()
    original = run_long_short_backtest(
        market_data=market_data,
        signal=signal,
        train_fraction=0.60,
        holdout_fraction=0.20,
        holding_period=5,
        rebalance_days=5,
        quantile=0.25,
        transaction_cost_bps=0.0,
    )
    changed = market_data.copy()
    holdout_dates = original.returns.index[original.returns.index >= original.holdout_start]
    changed.loc[
        changed.index.get_level_values("date").isin(holdout_dates),
        "adj_close",
    ] *= 1.5
    rerun = run_long_short_backtest(
        market_data=changed,
        signal=signal,
        train_fraction=0.60,
        holdout_fraction=0.20,
        holding_period=5,
        rebalance_days=5,
        quantile=0.25,
        transaction_cost_bps=0.0,
    )

    assert original.metrics["validation"] == rerun.metrics["validation"]
    assert original.metrics["test"] == original.metrics["validation"]
    assert original.holdout_start > original.validation_start
    assert original.metrics["holdout"] != rerun.metrics["holdout"]
```

Keep the fixture fully deterministic and ensure the modified prices affect only
forward returns whose decision dates are in holdout.

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_workflow.py -k "reserves_disjoint_holdout" -q
```

Expected: failure because `holdout_fraction`, `holdout_start`, and
`metrics["validation"]` do not exist.

- [ ] **Step 3: Implement split boundaries**

Extend `BacktestResult`:

```python
@dataclass(frozen=True)
class BacktestResult:
    raw_returns: pd.Series
    returns: pd.Series
    positions: pd.DataFrame
    ic_by_date: pd.Series
    turnover: pd.Series
    costs: pd.DataFrame
    metrics: dict[str, dict[str, float]]
    split_date: pd.Timestamp
    validation_start: pd.Timestamp
    holdout_start: pd.Timestamp
    walk_forward: list[WalkForwardWindow]
```

Add `holdout_fraction: float = 0.0` to `run_long_short_backtest`. For an enabled
holdout, calculate:

```python
holdout_size = max(1, int(np.ceil(len(returns) * holdout_fraction)))
holdout_position = len(returns) - holdout_size
train_position = min(max(int(len(returns) * train_fraction), 1), holdout_position - 1)
if train_position < 1 or holdout_position - train_position < 1:
    raise ValueError("not enough backtest observations for train, validation, and holdout")

split_date = pd.Timestamp(returns.index[train_position])
validation_start = pd.Timestamp(returns.index[train_position + 1])
holdout_start = pd.Timestamp(returns.index[holdout_position])
```

Build:

```python
train_metrics = summarize(returns.index <= split_date)
validation_metrics = summarize(
    (returns.index >= validation_start) & (returns.index < holdout_start)
)
holdout_metrics = summarize(returns.index >= holdout_start)
metrics = {
    "train": train_metrics,
    "validation": validation_metrics,
    "test": validation_metrics.copy(),
    "holdout": holdout_metrics,
    "full": full_metrics,
}
```

When the validity gate is disabled, preserve current behavior by using an empty
holdout and making validation/test equal to the old test period. Pass
`holdout_fraction` through baseline, stress, robustness, and capacity backtest
calls from `config.experiment.validation.research_validity`.

- [ ] **Step 4: Run focused and workflow tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_workflow.py tests/test_cli_e2e.py -q
```

Expected: all selected tests pass with existing `test` assertions preserved.

- [ ] **Step 5: Commit**

```bash
git add src/quant_research_agent/backtest src/quant_research_agent/agents tests/test_workflow.py
git commit -m "Reserve chronological research holdout"
```

### Task 3: Implement p-values, Benjamini-Hochberg correction, and verdicts

**Files:**
- Create: `src/quant_research_agent/agents/research_validity.py`
- Create: `tests/test_research_validity.py`
- Modify: `src/quant_research_agent/agents/robustness.py`

- [ ] **Step 1: Write failing statistical tests**

Create `tests/test_research_validity.py`:

```python
from quant_research_agent.agents.research_validity import (
    adjust_pvalues_benjamini_hochberg,
    one_sided_positive_pvalue,
)


def test_one_sided_positive_pvalue_decreases_with_tstat():
    assert one_sided_positive_pvalue(-1.0) > 0.5
    assert one_sided_positive_pvalue(0.0) == 0.5
    assert one_sided_positive_pvalue(2.0) < 0.05


def test_benjamini_hochberg_returns_monotonic_qvalues_in_original_order():
    adjusted = adjust_pvalues_benjamini_hochberg(
        {"agent_signal": 0.01, "baseline": 0.04, "stress": 0.03, "weak": 0.80}
    )

    assert adjusted["agent_signal"] == 0.04
    assert adjusted["baseline"] == pytest.approx(0.0533333333)
    assert adjusted["stress"] == pytest.approx(0.0533333333)
    assert adjusted["weak"] == 0.80
```

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_validity.py -q
```

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement pure statistical helpers and result types**

Create:

```python
@dataclass(frozen=True)
class CandidateEvidence:
    name: str
    family: str
    holdout_observations: int
    holdout_sharpe: float
    holdout_ic_mean: float
    holdout_ic_tstat: float
    holdout_total_return: float
    p_value: float
    q_value: float


@dataclass(frozen=True)
class ValidityCheck:
    name: str
    required: bool
    passed: bool | None
    observed: float | bool | str | None
    threshold: float | bool | str | None
    reason: str


@dataclass(frozen=True)
class ResearchValidityResult:
    enabled: bool
    verdict: str
    train_end: str
    validation_start: str
    holdout_start: str | None
    fdr_alpha: float
    candidates: list[CandidateEvidence]
    checks: list[ValidityCheck]
    reasons: list[str]


@dataclass(frozen=True)
class BacktestResultCandidate:
    name: str
    backtest: BacktestResult
```

Implement:

```python
def one_sided_positive_pvalue(tstat: float) -> float:
    if not math.isfinite(tstat):
        return 1.0
    return float(0.5 * math.erfc(tstat / math.sqrt(2.0)))


def adjust_pvalues_benjamini_hochberg(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    adjusted_sorted = [1.0] * count
    running = 1.0
    for reverse_index in range(count - 1, -1, -1):
        name, pvalue = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running, min(1.0, pvalue * count / rank))
        adjusted_sorted[reverse_index] = running
    return {
        name: adjusted_sorted[index]
        for index, (name, _) in enumerate(ordered)
    }
```

- [ ] **Step 4: Write failing verdict tests**

Use small `BacktestResult` builders with explicit holdout metrics. Cover:

```python
def _check(name: str, passed: bool, required: bool = True) -> ValidityCheck:
    return ValidityCheck(
        name=name,
        required=required,
        passed=passed,
        observed=passed,
        threshold=True,
        reason=name,
    )


def test_validity_promotes_when_all_required_checks_pass():
    checks = [
        _check("positive_holdout_sharpe", True),
        _check("positive_holdout_ic", True),
        _check("fdr_significant", True),
        _check("positive_holdout_return", True),
        _check("beats_best_baseline", True),
        _check("walk_forward_stable", True),
        _check("data_ready", True),
    ]

    assert select_validity_verdict(enabled=True, checks=checks) == "PROMOTE"


def test_validity_rejects_when_core_holdout_evidence_fails():
    checks = [
        _check("positive_holdout_sharpe", False),
        _check("positive_holdout_ic", True),
        _check("fdr_significant", True),
        _check("positive_holdout_return", True),
    ]

    assert select_validity_verdict(enabled=True, checks=checks) == "REJECT"


def test_validity_reviews_when_core_passes_but_data_is_not_ready():
    checks = [
        _check("positive_holdout_sharpe", True),
        _check("positive_holdout_ic", True),
        _check("fdr_significant", True),
        _check("positive_holdout_return", True),
        _check("data_ready", False),
    ]

    assert select_validity_verdict(enabled=True, checks=checks) == "REVIEW"


def test_candidate_evidence_uses_pvalue_one_for_insufficient_ic_observations():
    backtest = SimpleNamespace(
        metrics={
            "holdout": {
                "observations": 1.0,
                "sharpe": 1.0,
                "ic_mean": 0.05,
                "ic_tstat": 4.0,
                "total_return": 0.10,
            }
        }
    )

    evidence = build_candidate_evidence(
        name="agent_signal",
        family="primary",
        backtest=backtest,
    )

    assert evidence.p_value == 1.0
```

Assert exact verdict, check names, and reason text.

- [ ] **Step 5: Run and confirm RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_validity.py -q
```

Expected: helper tests pass; verdict tests fail because
`evaluate_research_validity` is missing.

- [ ] **Step 6: Implement family construction and verdict selection**

Implement:

```python
def evaluate_research_validity(
    *,
    config: AppConfig,
    agent: BacktestResult,
    baselines: dict[str, BacktestResult],
    stress_tests: dict[str, BacktestResult],
    parameter_variants: list[BacktestResultCandidate],
    cost_variants: list[BacktestResultCandidate],
    data_integrity: DataIntegrityReport,
) -> ResearchValidityResult:
    validity = config.experiment.validation.research_validity
    candidates = [
        build_candidate_evidence("agent_signal", "primary", agent),
        *[
            build_candidate_evidence(name, "baseline", backtest)
            for name, backtest in sorted(baselines.items())
        ],
        *[
            build_candidate_evidence(name, "stress_test", backtest)
            for name, backtest in sorted(stress_tests.items())
        ],
        *[
            build_candidate_evidence(item.name, "parameter_sensitivity", item.backtest)
            for item in parameter_variants
        ],
        *[
            build_candidate_evidence(item.name, "cost_sensitivity", item.backtest)
            for item in cost_variants
        ],
    ]
    qvalues = adjust_pvalues_benjamini_hochberg(
        {candidate.name: candidate.p_value for candidate in candidates}
    )
    adjusted = [
        replace(candidate, q_value=qvalues[candidate.name])
        for candidate in candidates
    ]
    checks = build_validity_checks(
        config=config,
        agent=agent,
        baselines=baselines,
        adjusted_candidates=adjusted,
        data_integrity=data_integrity,
    )
    verdict = select_validity_verdict(enabled=validity.enabled, checks=checks)
    reasons = [
        check.reason
        for check in checks
        if check.required and check.passed is False
    ]
    return ResearchValidityResult(
        enabled=validity.enabled,
        verdict=verdict,
        train_end=agent.split_date.date().isoformat(),
        validation_start=agent.validation_start.date().isoformat(),
        holdout_start=agent.holdout_start.date().isoformat(),
        fdr_alpha=validity.fdr_alpha,
        candidates=adjusted,
        checks=checks,
        reasons=reasons,
    )
```

Add `backtest: BacktestResult` to `SensitivityResult` so robustness variants
provide real holdout metrics instead of reconstructing evidence from validation
summary dictionaries. Implement `build_candidate_evidence`,
`build_validity_checks`, and `select_validity_verdict` in the same module.
`build_candidate_evidence` assigns p-value `1.0` when holdout IC observations
are below two. `build_validity_checks` returns the seven checks in design order,
including a non-required `beats_best_baseline` check with `passed=None` when no
baseline exists.

Verdict selection:

```python
core_names = {
    "positive_holdout_sharpe",
    "positive_holdout_ic",
    "fdr_significant",
    "positive_holdout_return",
}
failed_required = {
    check.name for check in checks
    if check.required and check.passed is False
}
if not validity.enabled:
    verdict = "REVIEW"
elif failed_required & core_names:
    verdict = "REJECT"
elif failed_required:
    verdict = "REVIEW"
else:
    verdict = "PROMOTE"
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_validity.py tests/test_workflow.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/quant_research_agent/agents/research_validity.py src/quant_research_agent/agents/robustness.py tests/test_research_validity.py
git commit -m "Evaluate research validity with FDR control"
```

### Task 4: Integrate validity into the workflow and report

**Files:**
- Modify: `src/quant_research_agent/agents/evaluator_agent.py`
- Modify: `src/quant_research_agent/agents/report_agent.py`
- Modify: `src/quant_research_agent/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Add failing workflow and report assertions**

Extend the main workflow test:

```python
assert result.research_validity.verdict in {"PROMOTE", "REVIEW", "REJECT"}
assert result.research_validity.holdout_start
assert {candidate.name for candidate in result.research_validity.candidates} >= {
    "agent_signal",
    "momentum_20d_only",
    "reversal_20d_only",
    "random_cross_section",
}
assert "Research Validity Gate" in report_text
assert f"Verdict: `{result.research_validity.verdict}`" in report_text
assert "FDR q-value" in report_text
assert "positive_holdout_sharpe" in report_text
```

Add a payload assertion by calling `workflow_payload` through the existing
configured workflow test:

```python
assert payload["research_validity"]["verdict"] == result.research_validity.verdict
assert payload["metrics"]["holdout"] == result.backtest.metrics["holdout"]
```

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_workflow.py -q
```

Expected: failures because `ResearchRunResult.research_validity`, report section,
and payload field do not exist.

- [ ] **Step 3: Integrate evaluator result**

Add to `ResearchRunResult`:

```python
research_validity: ResearchValidityResult
```

After capacity diagnostics:

```python
research_validity = evaluate_research_validity(
    config=config,
    agent=backtest,
    baselines=baselines,
    stress_tests=stress_tests,
    parameter_variants=[
        BacktestResultCandidate(item.name, item.backtest)
        for item in robustness.parameter_sensitivity
    ],
    cost_variants=[
        BacktestResultCandidate(item.name, item.backtest)
        for item in robustness.cost_sensitivity
    ],
    data_integrity=data_integrity,
)
```

Return it in `ResearchRunResult`.

- [ ] **Step 4: Render a deterministic report section**

Add `_research_validity_section(result)` that emits:

```markdown
## Research Validity Gate

Verdict: `REJECT`
Gate enabled: yes
Holdout starts: `2024-04-01`

| Candidate | Family | Holdout Obs | Holdout IC | Holdout Sharpe | Holdout Return | p-value | FDR q-value |
| agent_signal | primary | 44 | 0.0210 | 0.41 | 4.20% | 0.0310 | 0.0930 |

| Check | Required | Status | Observed | Threshold | Reason |
| positive_holdout_sharpe | yes | pass | 0.41 | > 0.00 | Holdout Sharpe clears the configured minimum. |
```

Place it before `Interpretation`. Replace broad promotion language in
`_interpretation` with verdict-aware text sourced from
`result.research_validity.reasons`.

- [ ] **Step 5: Add workflow payload serializer**

Implement `_research_validity_payload(result)` containing all dataclass fields
as JSON-safe primitives and add:

```python
"research_validity": _research_validity_payload(result),
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_workflow.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/quant_research_agent/agents/evaluator_agent.py src/quant_research_agent/agents/report_agent.py src/quant_research_agent/workflow.py tests/test_workflow.py
git commit -m "Expose research validity verdict"
```

### Task 5: Persist validity in CSV, reproducibility manifests, and registry metrics

**Files:**
- Modify: `src/quant_research_agent/agents/report_agent.py`
- Modify: `src/quant_research_agent/reproducibility.py`
- Test: `tests/test_cli_e2e.py`
- Test: `tests/test_production_research_platform.py`

- [ ] **Step 1: Add failing artifact assertions**

Extend CLI E2E:

```python
assert payload["research_validity"]["verdict"] in {"PROMOTE", "REVIEW", "REJECT"}
assert manifest["research_validity"] == payload["research_validity"]
assert manifest["metrics"]["holdout"] == payload["metrics"]["holdout"]
assert set(frame["validity_verdict"]) == {payload["research_validity"]["verdict"]}
assert frame["validity_enabled"].all()
assert frame["holdout_start"].notna().all()
assert frame["agent_fdr_q_value"].between(0.0, 1.0).all()
```

Extend the registry/API test:

```python
assert registry_record.metrics["holdout"] == payload["metrics"]["holdout"]
assert registry_record.metrics["research_validity"]["verdict"] == payload["research_validity"]["verdict"]
```

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_cli_e2e.py tests/test_production_research_platform.py -q
```

Expected: missing manifest/CSV/registry validity fields.

- [ ] **Step 3: Persist artifacts**

In `write_experiment_row`, add the same validity summary to every strategy and
window row:

```python
agent_evidence = next(
    item for item in result.research_validity.candidates
    if item.name == "agent_signal"
)
validity_columns = {
    "validity_verdict": result.research_validity.verdict,
    "validity_enabled": result.research_validity.enabled,
    "holdout_start": result.research_validity.holdout_start,
    "holdout_sharpe": agent_evidence.holdout_sharpe,
    "holdout_ic_mean": agent_evidence.holdout_ic_mean,
    "holdout_total_return": agent_evidence.holdout_total_return,
    "agent_fdr_q_value": agent_evidence.q_value,
}
```

In `write_reproducibility_pack`, add:

```python
"metrics": {
    "test": result.backtest.metrics["test"],
    "validation": result.backtest.metrics["validation"],
    "holdout": result.backtest.metrics["holdout"],
    "full": result.backtest.metrics["full"],
    "research_validity": research_validity_to_dict(result.research_validity),
},
"research_validity": research_validity_to_dict(result.research_validity),
```

Keep the top-level duplicate because readers need a direct decision surface,
while registry storage already captures the `metrics` object without a schema
migration.

- [ ] **Step 4: Run artifact tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_cli_e2e.py tests/test_production_research_platform.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant_research_agent/agents/report_agent.py src/quant_research_agent/reproducibility.py tests/test_cli_e2e.py tests/test_production_research_platform.py
git commit -m "Persist research validity evidence"
```

### Task 6: Enable the gate in checked-in configurations and prove all demos

**Files:**
- Modify: `configs/base.yaml`
- Modify: `configs/yahoo_nasdaq_demo.yaml`
- Modify: `configs/point_in_time_synthetic_demo.yaml`
- Modify: `configs/institutional_snapshot_demo.yaml`
- Test: `tests/test_cli_e2e.py`

- [ ] **Step 1: Add the validity block to all four configs**

Under `experiment.validation`:

```yaml
research_validity:
  enabled: true
  holdout_fraction: 0.15
  fdr_alpha: 0.10
  min_holdout_sharpe: 0.0
  min_holdout_ic: 0.0
  require_positive_return: true
  require_baseline_outperformance: true
  require_walk_forward_stability: true
  require_data_readiness: true
```

Do not weaken `require_data_readiness` for synthetic or Yahoo demos. Their
expected verdict may be `REVIEW` or `REJECT`; the purpose is to surface the
readiness failure honestly.

- [ ] **Step 2: Add the same block to temporary E2E configs**

This ensures artifact assertions test an enabled gate, not compatibility mode.

- [ ] **Step 3: Run deterministic demo smokes**

Run:

```bash
PYTHONPATH=src python -m quant_research_agent.main --config configs/base.yaml --json > /tmp/aiqra-base-validity.json
PYTHONPATH=src python -m quant_research_agent.main --config configs/point_in_time_synthetic_demo.yaml --json > /tmp/aiqra-pit-validity.json
PYTHONPATH=src python -m quant_research_agent.main --config configs/institutional_snapshot_demo.yaml --json > /tmp/aiqra-snapshot-validity.json
```

Expected: exit 0; each JSON file contains `research_validity.verdict`,
`metrics.validation`, and `metrics.holdout`.

- [ ] **Step 4: Run Yahoo smoke separately**

Before the external Yahoo step:

```bash
scripts/bin/harness-cli query tools --capability documentation-lookup --status present
PYTHONPATH=src python -m quant_research_agent.main --config configs/yahoo_nasdaq_demo.yaml --json > /tmp/aiqra-yahoo-validity.json
```

Expected: exit 0 when Yahoo is reachable. If Yahoo fails, record the exact
provider error as external validation friction without weakening deterministic
proof.

- [ ] **Step 5: Commit**

```bash
git add configs tests/test_cli_e2e.py
git commit -m "Enable validity gate in research demos"
```

### Task 7: Add Harness records and product documentation

**Files:**
- Create: `docs/stories/US-026-research-validity-promotion-gate/overview.md`
- Create: `docs/stories/US-026-research-validity-promotion-gate/design.md`
- Create: `docs/stories/US-026-research-validity-promotion-gate/execplan.md`
- Create: `docs/stories/US-026-research-validity-promotion-gate/validation.md`
- Create: `docs/decisions/0019-research-validity-promotion-gate.md`
- Modify: `README.md`
- Modify: `docs/product/ai-quant-research-agent.md`
- Modify: `docs/TEST_MATRIX.md`

- [ ] **Step 1: Record high-risk durable story and decision**

Run:

```bash
scripts/bin/harness-cli story add \
  --id US-026 \
  --title "Research validity and promotion gate" \
  --lane high-risk \
  --verify "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q"
scripts/bin/harness-cli decision add \
  --id 0019 \
  --title "Research validity and promotion gate" \
  --doc docs/decisions/0019-research-validity-promotion-gate.md
```

- [ ] **Step 2: Write story packet and decision**

Document the accepted methodology from
`docs/superpowers/specs/2026-06-18-us-026-research-validity-gate-design.md`,
including:

- Advisory verdict; no process failure on reject.
- Holdout excluded from development evidence.
- Complete within-run candidate family for BH correction.
- `test` retained as validation compatibility alias.
- No claim of cross-run false-discovery control.

- [ ] **Step 3: Update product docs**

Add to README and product contract:

- Three-way chronological split.
- FDR-adjusted significance.
- Exact promotion criteria.
- Artifact surfaces.
- Limitations of same-dataset tail holdout and within-run FDR.

Remove `multiple-hypothesis controls` from the list of missing v1 features and
replace it with `cross-run experiment-family controls` as the remaining gap.

- [ ] **Step 4: Run documentation checks**

Run:

```bash
rg -n "Research Validity Gate|PROMOTE|Benjamini-Hochberg|holdout" README.md docs/product docs/stories/US-026-research-validity-promotion-gate docs/decisions/0019-research-validity-promotion-gate.md
git diff --check
```

Expected: all concepts are present and diff check exits 0.

- [ ] **Step 5: Commit**

```bash
git add README.md docs
git commit -m "Document US-026 validity methodology"
```

### Task 8: Full verification and Harness closeout

**Files:**
- Modify only if verification exposes a defect.

- [ ] **Step 1: Run focused validity tests**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_research_validity.py tests/test_workflow.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run full suite**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Expected: all tests pass with no collection errors.

- [ ] **Step 3: Run static/runtime checks**

```bash
python -m compileall -q src tests
python -m pip check
git diff --check
```

Expected: all commands exit 0 and pip reports no broken requirements.

- [ ] **Step 4: Run story verification**

```bash
scripts/bin/harness-cli story verify US-026
scripts/bin/harness-cli story update \
  --id US-026 \
  --status implemented \
  --unit 1 \
  --integration 1 \
  --e2e 1 \
  --platform 1 \
  --evidence "Validity unit, workflow, CLI artifact, full pytest, compileall, pip check, and deterministic config smokes passed."
scripts/bin/harness-cli query matrix
```

Expected: US-026 shows `implemented`, all proof columns `yes`, and verification
result `pass`.

- [ ] **Step 5: Record final trace**

```bash
scripts/bin/harness-cli trace \
  --summary "Implemented US-026 research validity and promotion gate" \
  --outcome completed
```

- [ ] **Step 6: Inspect final repository state**

```bash
git status --short --branch
git log --oneline --decorate -10
```

Expected: only intentional uncommitted Harness database state is ignored; source
work is committed and the branch is ahead of `origin/main`.
