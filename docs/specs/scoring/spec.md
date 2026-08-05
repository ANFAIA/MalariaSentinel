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
| Version | `v1.2` (runner API); composite v1.2 (D1..D16 weighted geometric mean, D12-D15 optional) |
| Status | `stable` (runner); `stable` (D1-D10); `stable` (D12-D15, optional); `stable` (D16); `draft` (LLM scorer) |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-08-05` |

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
- The scorer suite at `mal-core/src/mal_core/abm/tests/calibration/scorers/` (D1..D16 + LLM scorer).
- **Optional scorers** (D12–D15) are always registered in `ALL_SCORERS` but gracefully fall back to `score=0` when their required data is absent from `run_dir` or `experiment`.
- The composite (`composite.geometric_mean`, `DEFAULT_WEIGHTS`).
- The feedback report (`get_feedback(scorecard, baseline=None) -> str`).
- The diff renderer (`diff_scorecards(a, b, best=None) -> str`).
- The best-tracker (`load_best`, `save_best`, `update_best`).
- The report renderer (`verdict_label`, `dimension_status`, `render_report`).
- The scorecard runner (`score_run`, `save_scorecard`).
- Tier markers (`fast`, `full`, `llm`).
- Flag schema (`SCORING_FLAGS_SCHEMA`, `ScoringFlags`).
- Pipeline position: stage 4 (after abm).

## 3. Out of scope

- ABM output contract → `docs/specs/abm/spec.md`.
- Calibration suite authoring (scorer implementation details) → each scorer's docstring + the `calibration-test-framework.md` plan.
- Production deployment of the LLM scorer (in `prompts/`) → out of scope until the LLM scorer is `stable`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `run_calibration(run_dir, tier="fast", output_dir=None, experiment_name="pipeline_run") -> dict` | `mal_core.scoring.runner` | Runs `pytest -m <tier>`. Returns `{"success": bool, "stdout": str, "stderr": str, "returncode": int}`. |
| `get_feedback(scorecard: dict, baseline: dict \| None = None) -> str` | `mal_core.scoring.feedback` | Generates a markdown feedback string with delta vs baseline. |
| `diff_scorecards(a: dict, b: dict, best: dict \| None = None) -> str` | `mal_core.abm.tests.calibration.scorers.diff` | Dual-delta markdown table: prev vs current vs best. |
| `load_best(run_dir) -> dict \| None` | `mal_core.abm.tests.calibration.scorers.best` | Load best historical scorecard from run_dir parent. |
| `save_best(scorecard, run_dir) -> None` | `mal_core.abm.tests.calibration.scorers.best` | Persist best scorecard. |
| `update_best(current, run_dir) -> (bool, dict \| None)` | `mal_core.abm.tests.calibration.scorers.best` | Compare current vs best; update if current composite is higher. Returns `(updated, previous_best)`. |
| `score_run(run_dir, experiment) -> dict` | `mal_core.abm.tests.calibration.scorers.score` | Run all scorers on a run directory. Returns a scorecard dict (JSON-serialisable). |
| `save_scorecard(scorecard, path) -> None` | `mal_core.abm.tests.calibration.scorers.score` | Persist scorecard to JSON. |
| `verdict_label(composite) -> str` | `mal_core.abm.tests.calibration.report` | Returns `"VIABLE"`, `"BORDERLINE"`, `"REGRESSED"`, or `"COLLAPSED"`. |
| `dimension_status(score, min_score, hard_floor) -> str` | `mal_core.abm.tests.calibration.report` | Returns `"OK"`, `"REGRESSED"`, or `"COLLAPSED"` per dimension. |
| `render_report(report: ScoringReport, thresholds: dict) -> str` | `mal_core.abm.tests.calibration.report` | Render a `ScoringReport` as markdown with verdict, params, dimension table, and LLM verdict block. |
| `geometric_mean(scores, weights=None) -> float` | `mal_core.abm.tests.calibration.scorers.composite` | Weighted geometric mean. Returns 0.0 if any score is `<= 0.0`. |
| `DEFAULT_WEIGHTS` | `mal_core.abm.tests.calibration.scorers.composite` | Per-scorer weight dict. Adding a scorer requires adding its weight here. |
| `ScorerResult` | `mal_core.abm.tests.calibration.scorers.base` | Dataclass: `score`, `value`, `target`, `diagnostics`, `passed`. |
| `ScoringReport` | `mal_core.abm.tests.calibration.scorers.base` | Dataclass: `experiment_name`, `params`, `n_days`, `n_seeds`, `scores`, `composite`, `llm_verdict`. |
| `Scorer` (ABC) | `mal_core.abm.tests.calibration.scorers.base` | Abstract base: `name`, `weight`, `score(run_dir, experiment) -> ScorerResult`. |
| `SCORING_FLAGS_SCHEMA`, `ScoringFlags` | `mal_core.scoring.flags` | Pydantic-style: `tier`, `experiment_name`. |

## 5. Invariants

### §5.1 Runner

- **INV-1.** `run_calibration` invokes `pytest` as a subprocess (not an in-process call). The subprocess inherits `cwd=<mal-core>/src/mal_core/abm/`, and sets `CALIBRATION_TIER=<tier>` in env.
- **INV-2.** `tier` must be one of `"fast"`, `"full"`, or `"llm"`. Unknown tiers pass through to pytest's marker filter (which silently filters everything); `run_calibration` does not validate. When running outside `run_calibration` (direct `pytest`), the default tier in `conftest.py` is `"full"` if `CALIBRATION_TIER` is unset.
- **INV-3.** `run_calibration` does **not** raise on test failures. The `success` field in the return dict encodes pass/fail. Pipeline consumers decide what to do.
- **INV-4.** `experiment_name` is informational only (passed via env to scorers that read it). No semantic effect on the score.

### §5.2 Scorer suite (D1..D16 + LLM)

- **INV-5.** Each scorer lives at `mal-core/src/mal_core/abm/tests/calibration/scorers/D<id>_<name>.py` (or `<name>.py` for the un-numbered D1..D10 original suite). It exports `score(run_dir, experiment) -> ScorerResult` via the `Scorer` ABC.
- **INV-6.** Scorer IDs are stable: `D1` expansion, `D2` survival/mortality, `D3` EIP, `D4` stability, `D5` Moran's I (spatial), `D6` mass conservation, `D7` determinism, `D8` coupling, `D9` activation, `D10` performance, `D11` larval dynamics, `D12` host density, `D13` host-seeking distance, `D14` mobility conservation, `D15` long-horizon persistence, `D16` suitability AUC.
- **INV-6b.** Optional scorer dependencies — when the required data is missing the scorer returns `score=0` (graceful fallback, no exception):
  | Scorer | Required data | Source |
  |---|---|---|
  | D12 host density | `host_static.nc` in `run_dir` parent or `data/<aoi>/` | `ingest --what hosts` |
  | D13 host-seeking distance | `host_seeking_scale_m` in `experiment` dict | ABM parameter set |
  | D14 mobility conservation | `*.csr` files (OD matrices) in `run_dir` parent or `data/<aoi>/` | `ingest --what mobility` |
  | D15 long-horizon persistence | `*_day*_aquatic.json` files spanning ≥365 days + `state_day*.tif` COGs | Long ABM runs (≥365 days) |
- **INV-7.** Adding a scorer = adding a new file in `scorers/` + appending to `DEFAULT_WEIGHTS` in `composite.py`. This is **non-breaking** (MINOR).
- **INV-8.** Removing a scorer = MAJOR. Requires bumping the composite and re-running all historical scorecards (they become non-comparable).

### §5.3 Composite

- **INV-9.** Composite = weighted geometric mean: `exp(Σ wi · log(si) / Σ wi)`. Returns 0.0 if any `si <= 0.0`.
- **INV-10.** `DEFAULT_WEIGHTS` is the single source of truth for per-scorer weights. Default weights today:
  - `D1..D10` original suite: `D1=2, D2=3, D3=2, D4=3, D5=1, D6=2, D7=2, D8=2, D9=1, D10=1`.
  - D11–D16: `D11=1, D12=2, D13=2, D14=2, D15=3, D16=2`.
- **INV-11.** Composite handles variable scorer counts automatically via the geometric mean (missing scorers ⇒ absent from numerator and denominator). This means adding a scorer does not break historical composites — it just narrows what they cover.

### §5.4 LLM scorer

- **INV-12.** `scorers/llm_scorer.py` is the LLM-as-judge component. Status: `draft`. It must not gate `stable` runs until promoted.
- **INV-13.** LLM scorer prompts live at `scorers/prompts/`. Prompts are versioned alongside the scorer file. **Prompts must not change without bumping the scorer's effective version** (see §7).
- **INV-17.** The LLM scorer uses OpenRouter (`https://openrouter.ai/api/v1`) via `requests`, not langchain_openai. API key is resolved from `OPENROUTER_KEY` env var or `.env` file. Default model: `minimax/minimax-m3`. Verdicts are content-hash cached under `.cache/llm_verdicts/`.

### §5.5 Feedback

- **INV-14.** `get_feedback` returns a markdown string. If `scorecard["success"]` is True → reports "All calibration tests passed". If False → includes up to 500 chars of `stderr`.
- **INV-15.** When `baseline` is provided, `get_feedback` classifies the delta as `regression` (baseline passed, current failed) or `improvement` (baseline failed, current passed) and emits the matching markdown section.

### §5.6 Pipeline integration

- **INV-16.** `pipeline/spec.md` dispatches `Stage.SCORING → run_calibration(run_dir=output_dir/abm, output_dir=output_dir/scoring, **extra)`. The run_dir must exist and contain ABM rollouts (per `abm/spec.md` §5).

## 6. Data contracts

- **Inputs:** ABM rollouts under `run_dir` matching `state_seed*_day*.{tif,npy}` (per `abm/spec.md` §5.1, §5.3).
- **Optional inputs (D12–D15):**
  - `host_static.nc` — NetCDF with `human`, `cattle`, `goats`, `pigs`, `sheep` layers. Produced by `malariasim ingest --aoi <aoi> --what hosts`.
  - `*.csr` — CSR binary OD matrices (`*_mobility_day.csr`, `*_mobility_night.csr`, `*_livestock_mobility.csr`). Produced by `malariasim ingest --aoi <aoi> --what mobility`.
  - `*_day*_aquatic.json` + `state_day*.tif` — daily snapshot files from long ABM runs (≥365 days). Produced by `malariasim abm --aoi <aoi> --days 365`.
- **Outputs:** Scorecard persisted as `scorecard.json` under `run_dir` (via `save_scorecard`). The runner also returns pytest stdout/stderr in its return dict.

## 7. Migration & deprecation

- **Adding a scorer (D<n+1>)**: bump MINOR. Add the scorer file, append to `DEFAULT_WEIGHTS`, document the new ID in §5.2.
- **Removing a scorer**: bump MAJOR. The composite changes shape; all historical scorecards become non-comparable.
- **Bumping `tier` semantics** (e.g. adding `slow`): bump MINOR. Update `run_calibration` validation in §5.1 INV-2.
- **Promoting the LLM scorer from `draft` to `stable`**: bump MINOR. Move §5.4 INV-12 status.
- **Scorecard persistence**: `score_run` writes `scorecard.json` under `run_dir` via `save_scorecard`. The diff renderer (`diff_scorecards`) and best-tracker (`update_best`) consume these scorecards.
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
          'spatial', 'stability', 'suitability_auc'}
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

# INV-10: DEFAULT_WEIGHTS has every D1..D16 entry
uv run python -c "
from mal_core.abm.tests.calibration.scorers.composite import DEFAULT_WEIGHTS
required = {'D1_expansion','D2_survival','D3_eip','D4_stability','D5_morans','D6_mass',
            'D7_determinism','D8_coupling','D9_activation','D10_perf','D11_larval_dynamics',
            'D12_host_density','D13_host_seeking_distance','D14_mobility_conservation','D15_long_horizon_persistence',
            'D16_suitability_auc'}
missing = required - set(DEFAULT_WEIGHTS)
assert not missing, f'missing weights for: {missing}'
"

# INV-10b: D12-D15 are wired in ALL_SCORERS
uv run python -c "
from mal_core.abm.tests.calibration.scorers.score import ALL_SCORERS
names = {s.name for s in ALL_SCORERS}
required = {'D12_host_density','D13_host_seeking_distance','D14_mobility_conservation','D15_long_horizon_persistence'}
missing = required - names
assert not missing, f'D12-D15 not wired in ALL_SCORERS: {missing}'
"

# INV-1/2: run_calibration subprocess contract
rg "subprocess.run" mal-core/src/mal_core/scoring/runner.py
rg "CALIBRATION_TIER" mal-core/src/mal_core/scoring/runner.py

# INV-12: LLM scorer still in draft, uses OpenRouter
rg "draft" docs/specs/scoring/spec.md | head -1
rg "openrouter" mal-core/src/mal_core/abm/tests/calibration/scorers/llm_scorer.py | head -1
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
# Diff two scorecards
from mal_core.abm.tests.calibration.scorers.diff import diff_scorecards
from mal_core.abm.tests.calibration.scorers.best import load_best
from pathlib import Path

run_dir = Path("runs/abm-2024-07")
best = load_best(run_dir)
report = diff_scorecards(previous_scorecard, current_scorecard, best=best)
print(report)
```

```python
# Render a full calibration report
from mal_core.abm.tests.calibration.report import render_report, verdict_label
from mal_core.abm.tests.calibration.scorers.base import ScoringReport
import yaml

thresholds = yaml.safe_load(open("mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml"))
report = ScoringReport(experiment_name="m-perf-f2", params={}, n_days=90, n_seeds=5, composite=0.72)
print(render_report(report, thresholds))
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