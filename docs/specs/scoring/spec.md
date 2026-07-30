# scoring Spec

> Owns the **calibration framework**: running biological/dynamical
> scorers against ABM rollouts, computing the composite score, and
> emitting feedback for the next iteration.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: abm
    direction: upstream
    reason: scoring runs pytest against ABM rollouts; scorers consume ABM state tensors
    severity: breaking
  - target: pipeline
    direction: bidirectional
    reason: pipeline dispatches Stage.SCORING → run_calibration
    severity: breaking
  - target: data
    direction: upstream
    reason: scoring reads ABM output paths and sidecars via data spec naming
    severity: non-breaking
  - target: commonlib
    direction: upstream
    reason: scoring runs from commonlib-anchored paths
    severity: non-breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: [adr-spec-design-2026-07-30]
  patterns: []
  pitfalls: []
  tools: []
```

## Metadata

| Field | Value |
|---|---|
| Component | `mal-core/src/mal_core/scoring/` + `mal-core/src/mal_core/abm/tests/calibration/` |
| Version | `v1.0` (runner API); composite v1.0 (D1..D15 weighted geometric mean) |
| Status | `stable` (runner); `stable` (D1-D10); `stable` (D11-D15); `draft` (LLM scorer) |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

Scoring is the **calibration truth-test**. It runs a battery of
biological/dynamical scorers against ABM rollouts to produce a single
composite number that tells the team whether the simulation is
realistic. Without scoring the system would have no objective way to
say "the ABM matches the real world" or "this parameter change made
things worse".

The composite is what gates M-perf and M3-M4: every ABM change must
beat the previous best composite on the same benchmark before
promoting.

## 2. In scope

- `run_calibration(run_dir, tier="fast", output_dir=None, experiment_name="pipeline_run") -> dict`.
- The pytest integration (`pytest -m <tier>`, sets `CALIBRATION_TIER` env).
- The scorer suite at `mal-core/src/mal_core/abm/tests/calibration/scorers/` (D1..D15 + LLM scorer).
- The composite (`composite.geometric_mean`, `DEFAULT_WEIGHTS`).
- The feedback report (`get_feedback(scorecard, baseline=None) -> str`).
- Tier markers (`fast`, `full`).
- Flag schema (`SCORING_FLAGS_SCHEMA`, `ScoringFlags`).

## 3. Out of scope

- ABM output contract → `docs/specs/abm/spec.md`.
- Calibration suite authoring (scorer implementation details) → each scorer's docstring + the `agstack` calibration framework conventions.
- Production deployment of the LLM scorer (in `prompts/`) → out of scope until the LLM scorer is `stable`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `run_calibration(run_dir, tier="fast", output_dir=None, experiment_name="pipeline_run") -> dict` | `mal_core.scoring.runner` | Runs `pytest -m <tier>`. Returns `{"success": bool, "stdout": str, "stderr": str, "returncode": int}`. |
| `get_feedback(scorecard: dict, baseline: dict | None = None) -> str` | `mal_core.scoring.feedback` | Generates a markdown feedback string with delta vs baseline. |
| `geometric_mean(scores, weights=None) -> float` | `mal_core.abm.tests.calibration.scorers.composite` | Weighted geometric mean. Returns 0.0 if any score is `<= 0.0`. |
| `DEFAULT_WEIGHTS` | `mal_core.abm.tests.calibration.scorers.composite` | Per-scorer weight dict. Adding a scorer requires adding its weight here. |
| `SCORING_FLAGS_SCHEMA`, `ScoringFlags` | `mal_core.scoring.flags` | Pydantic-style: `tier`, `experiment_name`. |

## 5. Invariants

### §5.1 Runner

- **INV-1.** `run_calibration` invokes `pytest` as a subprocess (not an in-process call). The subprocess inherits `cwd=<mal-core>/src/mal_core/abm/tests/calibration/..`, and sets `CALIBRATION_TIER=<tier>` in env.
- **INV-2.** `tier` must be one of `"fast"`, `"full"`. Unknown tiers pass through to pytest's marker filter (which silently filters everything); `run_calibration` does not validate.
- **INV-3.** `run_calibration` does **not** raise on test failures. The `success` field in the return dict encodes pass/fail. Pipeline consumers decide what to do.
- **INV-4.** `experiment_name` is informational only (passed via env to scorers that read it). No semantic effect on the score.

### §5.2 Scorer suite (D1..D15 + LLM)

- **INV-5.** Each scorer lives at `mal-core/src/mal_core/abm/tests/calibration/scorers/D<id>_<name>.py` (or `<name>.py` for the un-numbered D1..D10 original suite). It exports `score(rollout) -> ScorerResult` or a pytest-style function that returns the same shape.
- **INV-6.** Scorer IDs are stable: `D1` expansion, `D2` survival/mortality, `D3` EIP, `D4` stability, `D5` Moran's I (spatial), `D6` mass conservation, `D7` determinism, `D8` coupling, `D9` activation, `D10` performance, `D11` larval dynamics, `D12` host density, `D13` host-seeking distance, `D14` mobility conservation, `D15` long-horizon persistence.
- **INV-7.** Adding a scorer = adding a new file in `scorers/` + appending to `DEFAULT_WEIGHTS` in `composite.py`. This is **non-breaking** (MINOR).
- **INV-8.** Removing a scorer = MAJOR. Requires bumping the composite and re-running all historical scorecards (they become non-comparable).

### §5.3 Composite

- **INV-9.** Composite = weighted geometric mean: `exp(Σ wi · log(si) / Σ wi)`. Returns 0.0 if any `si <= 0.0`.
- **INV-10.** `DEFAULT_WEIGHTS` is the single source of truth for per-scorer weights. Default weights today:
  - `D1..D10` original suite: `D1=2, D2=3, D3=2, D4=3, D5=1, D6=2, D7=2, D8=2, D9=1, D10=1`.
  - D11–D15: `D11=1, D12=2, D13=2, D14=2, D15=3`.
- **INV-11.** Composite handles variable scorer counts automatically via the geometric mean (missing scorers ⇒ absent from numerator and denominator). This means adding a scorer does not break historical composites — it just narrows what they cover.

### §5.4 LLM scorer

- **INV-12.** `scorers/llm_scorer.py` is the LLM-as-judge component. Status: `draft`. It must not gate `stable` runs until promoted.
- **INV-13.** LLM scorer prompts live at `scorers/prompts/`. Prompts are versioned alongside the scorer file. **Prompts must not change without bumping the scorer's effective version** (see §7).

### §5.5 Feedback

- **INV-14.** `get_feedback` returns a markdown string. If `scorecard["success"]` is True → reports "All calibration tests passed". If False → includes up to 500 chars of `stderr`.
- **INV-15.** When `baseline` is provided, `get_feedback` classifies the delta as `regression` (baseline passed, current failed) or `improvement` (baseline failed, current passed) and emits the matching markdown section.

### §5.6 Pipeline integration

- **INV-16.** `pipeline/spec.md` dispatches `Stage.SCORING → run_calibration(run_dir=output_dir/abm, output_dir=output_dir/scoring, **extra)`. The run_dir must exist and contain ABM rollouts (per `abm/spec.md` §5).

## 6. Data contracts

- **Inputs:** ABM rollouts under `run_dir` matching `state_seed*_day*.{tif,npy}` (per `abm/spec.md` §5.1, §5.3).
- **Outputs:** pytest stdout/stderr captured by `run_calibration`. Scorecard is reconstructible from the pytest report (no separate scorecard file is written today — see §7).

## 7. Migration & deprecation

- **Adding a scorer (D<n+1>)**: bump MINOR. Add the scorer file, append to `DEFAULT_WEIGHTS`, document the new ID in §5.2.
- **Removing a scorer**: bump MAJOR. The composite changes shape; all historical scorecards become non-comparable.
- **Bumping `tier` semantics** (e.g. adding `slow`): bump MINOR. Update `run_calibration` validation in §5.1 INV-2.
- **Promoting the LLM scorer from `draft` to `stable`**: bump MINOR. Move §5.4 INV-12 status.
- **Scorecard persistence**: today the runner returns pytest stdout/stderr; there is no persisted JSON scorecard. Adding a persisted scorecard (machine-readable diff vs baseline) is a planned MAJOR.
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-5: every scorer file follows the naming convention
uv run python -c "
import os
d = 'mal-core/src/mal_core/abm/tests/calibration/scorers'
files = {f[:-3] for f in os.listdir(d) if f.endswith('.py') and not f.startswith('_')}
files -= {'base', 'score', 'composite', 'best', 'diff', 'activation', 'coupling', 'determinism', 'eip',
          'expansion', 'larval_dynamics', 'llm_scorer', 'mass', 'mortality', 'performance',
          'spatial', 'stability'}
# remaining files should match D<N>_<name> pattern
import re
for f in files:
    assert re.match(r'^D\d+_\w+$', f), f'scorer {f} violates D<id>_<name> convention'
"

# INV-9: composite is geometric mean
uv run python -c "
import math
from mal_core.abm.tests.calibration.scorers.composite import geometric_mean, DEFAULT_WEIGHTS
from scorers.base import ScorerResult
scores = {k: ScorerResult(score=0.8, weight=1.0) for k in DEFAULT_WEIGHTS}
got = geometric_mean(scores, DEFAULT_WEIGHTS)
expected = math.exp(sum(DEFAULT_WEIGHTS.values() * math.log(0.8)) / sum(DEFAULT_WEIGHTS.values()))
assert abs(got - expected) < 1e-9, f'{got} vs {expected}'
"

# INV-9 edge case: any score <= 0 collapses to 0
uv run python -c "
from mal_core.abm.tests.calibration.scorers.composite import geometric_mean, DEFAULT_WEIGHTS
from scorers.base import ScorerResult
scores = {k: ScorerResult(score=0.0 if k == 'D1_expansion' else 0.8, weight=1.0) for k in DEFAULT_WEIGHTS}
assert geometric_mean(scores, DEFAULT_WEIGHTS) == 0.0
"

# INV-10: DEFAULT_WEIGHTS has every D1..D15 entry
uv run python -c "
from mal_core.abm.tests.calibration.scorers.composite import DEFAULT_WEIGHTS
required = {'D1_expansion','D2_survival','D3_eip','D4_stability','D5_morans','D6_mass',
            'D7_determinism','D8_coupling','D9_activation','D10_perf','D11_larval_dynamics',
            'D12_host_density','D13_host_seeking_distance','D14_mobility_conservation','D15_long_horizon_persistence'}
missing = required - set(DEFAULT_WEIGHTS)
assert not missing, f'missing weights for: {missing}'
"

# INV-1/2: run_calibration subprocess contract
rg "subprocess.run" mal-core/src/mal_core/scoring/runner.py
rg "CALIBRATION_TIER" mal-core/src/mal_core/scoring/runner.py

# INV-12: LLM scorer still in draft
rg "draft" docs/specs/scoring/spec.md | head -1
```

## 9. Examples

```python
# Run the fast tier (PR gate)
from mal_core.scoring import run_calibration
from pathlib import Path

result = run_calibration(
    run_dir=Path("runs/abm-2024-07"),
    tier="fast",
    experiment_name="m-perf-f2",
)
assert result["success"], "calibration failed; see stderr"
```

```python
# Compute the composite from a scorecard
import math
from mal_core.abm.tests.calibration.scorers.composite import geometric_mean, DEFAULT_WEIGHTS
from scorers.base import ScorerResult

scores = {
    "D1_expansion": ScorerResult(score=0.85, weight=1.0),
    "D2_survival": ScorerResult(score=0.92, weight=1.0),
    # ... etc
}
print(f"composite = {geometric_mean(scores, DEFAULT_WEIGHTS):.4f}")
```

```python
# Feedback for the next iteration
from mal_core.scoring.feedback import get_feedback

report = get_feedback(current_scorecard, baseline=previous_scorecard)
print(report)  # markdown string
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `abm`, `pipeline`, `data`, `commonlib`.
- AGENTS.md section: "Calibration framework conventions" (AGENTS.md).
- Plan: `calibration-test-framework.md` (in `docs/plans/completed/`).
- External: Beven & Kirkby (1979) for TWI; Huestis & Lehmann (2019) for *Anopheles* dispersal cited from dispersal plans.