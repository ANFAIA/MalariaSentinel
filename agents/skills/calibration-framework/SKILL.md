---
name: calibration-framework
description: Understand and extend the ABM calibration scorecard framework. Covers the 11 scorer dimensions, composite scoring, thresholds, how to add new scorers, and how to interpret results. Use when adding biological features to the ABM, writing new scorers, or debugging calibration regressions.
---

# Calibration Framework

## Overview

The calibration framework scores mal-abm-fast C++ ABM rollouts against biological, physical, and computational expectations. It runs 11 deterministic scorers (D1-D11) that each evaluate one dimension of the simulation, then combines them into a single composite score via weighted geometric mean. An optional LLM judge (D12) provides a qualitative verdict on the same report.

The framework lives at `mal-abm-fast/tests/calibration/` and is a separate workspace member.

## Quick reference

```bash
# From the calibration directory (mal-abm-fast/tests/calibration/)
uv run pytest -m fast -v          # 10 scorers, 1 seed, 30 days (PR gate)
uv run pytest -m full -v          # 10 scorers + LLM, 5 seeds, 90 days
uv run pytest -m llm -v           # LLM judge only (requires OPENCODE_API_KEY)

# Score a single run directory
uv run python -m scorers.score --run-dir <path> [--experiment <name>]

# Diff two scorecards
uv run python -m scorers.diff scorecard_a.json scorecard_b.json [--best best.json]
```

Tier selection is via `CALIBRATION_TIER` env var (`fast` or `full`). LLM tests require `OPENCODE_API_KEY`.

## The 11 dimensions

| Dim | Scorer | What it measures | Target | Source |
|---|---|---|---|---|
| D1 | `expansion.py` | Fraction of AOI with non-zero density (habitat coverage spread) | 0.02-0.10 | Thomas 2013, Costantini 1996 |
| D2 | `mortality.py` | Adult daily survival rate (mean lifespan from steady-state) | 8-15 days | Saarman 2019, Midega 2007 |
| D3 | `eip.py` | EIP completion fraction at day 30 | 0.20-0.50 | Mordecai 2013 |
| D4 | `stability.py` | Population stability (no extinction, no explosion) | collapse 0.10-0.80, explosion <=5.0 | Internal (wire.hpp:80, M7.0) |
| D5 | `spatial.py` | Moran's I spatial autocorrelation on active habitat pixels | 0.20-0.70 | Bissett 2026, Tokarz & Novak 2018 |
| D6 | `mass.py` | Mass conservation (all pixel values in [0,1]) | 1.00 | pitfall-abm-nan-cog-write |
| D7 | `determinism.py` | Binary determinism check (same seed = same output) | 1.00 | F1.f milestone |
| D8 | `coupling.py` | Density-suitability correlation (Pearson r) | >=0.30 r | C1 fix commit |
| D9 | `activation.py` | Patch activation fraction across timesteps | 0.05-0.30 | wire.hpp:107-118 |
| D10 | `performance.py` | Wall-clock time per rollout | <=30s | M-perf F1.g target |
| D11 | `larval_dynamics.py` | Larval fraction of total population | 30-60% | Mordecai 2013 |

## Composite scoring

The composite is a **weighted geometric mean** of D1-D11 scores. Implemented in `scorers/composite.py::geometric_mean()`.

```python
DEFAULT_WEIGHTS = {
    "D1_expansion": 2.0, "D2_survival": 3.0, "D3_eip": 2.0,
    "D4_stability": 3.0, "D5_morans": 1.0, "D6_mass": 2.0,
    "D7_determinism": 2.0, "D8_coupling": 2.0, "D9_activation": 1.0,
    "D10_perf": 1.0, "D11_larval_dynamics": 1.0,
}
```

The formula: `composite = exp( sum(w_i * log(score_i)) / sum(w_i) )`

If any scorer returns `score <= 0.0`, the composite is `0.0` (geometric mean property). D2 (survival) and D4 (stability) carry the highest weight (3.0) because they are the most biologically critical dimensions.

## Thresholds

Each dimension has three thresholds in `thresholds.yaml`:

| Threshold | Meaning | Action |
|---|---|---|
| `min_score` | Below this, the dimension is "regressed" | Fail the PR gate |
| `max_delta` | Score dropped more than this vs baseline | Flag regression |
| `hard_floor` | Below this, the dimension is "collapsed" | Hard failure |

Current values from `thresholds.yaml`:

| Dim | min_score | max_delta | hard_floor |
|---|---|---|---|
| D1_expansion | 0.50 | -0.30 | 0.10 |
| D2_survival | 0.50 | -0.40 | 0.20 |
| D3_eip | 0.30 | -0.40 | 0.10 |
| D4_stability | 0.70 | -0.20 | 0.30 |
| D5_morans | 0.50 | -0.30 | 0.20 |
| D6_mass | 0.99 | -0.01 | 0.95 |
| D7_determinism | 0.99 | -0.01 | 0.95 |
| D8_coupling | 0.40 | -0.40 | 0.10 |
| D9_activation | 0.40 | -0.40 | 0.10 |
| D10_perf | 0.70 | -0.30 | 0.30 |
| D11_larval_dynamics | 0.70 | -0.15 | 0.50 |

## Adding a new scorer

1. **Create the scorer file**: `scorers/D<id>_<name>.py` where `<id>` is the next number (D12, D13, ...). Implement the `Scorer` ABC from `scorers/base.py`:

   ```python
   from scorers.base import Scorer, ScorerResult

   class MyNewScorer(Scorer):
       @property
       def name(self) -> str:
           return "D12_my_new"

       @property
       def weight(self) -> float:
           return 1.0

       def score(self, run_dir, experiment) -> ScorerResult:
           # Your scoring logic here
           return ScorerResult(score=0.85, value=..., target="...", diagnostics={...})
   ```

2. **Register in thresholds.yaml**: Add a new entry with `min_score`, `max_delta`, `hard_floor`, and `source`.

3. **Add weight to composite**: Add `"D12_my_new": 1.0` to `DEFAULT_WEIGHTS` in `scorers/composite.py`.

4. **Register in ALL_SCORERS**: Import and append to `ALL_SCORERS` in `scorers/score.py`.

5. **Run tests**:
   ```bash
   cd mal-abm-fast/tests/calibration
   uv run pytest -m fast -v
   ```

6. **Verify the diff report** shows the new dimension and no regressions.

## Scorer naming convention

Files: `D<id>_<name>.py` — e.g. `D1_expansion.py`, `D11_larval_dynamics.py`.

The `<id>` is sequential (D1 through D11 currently). The `<name>` is a short snake_case description. The scorer's `name` property must match `D<id>_<name>` exactly (used as the key in scorecards and `DEFAULT_WEIGHTS`).

## LLM verdict

The LLM judge (`scorers/llm_scorer.py`) sends the full calibration report JSON to a small LLM (default: `minimax-m3`) via the OpenCode Zen chat/completions API. It returns a structured `Verdict` with:

- **verdict**: `viable` / `borderline` / `regressed` / `collapsed`
- **composite_estimate**: LLM's holistic score in [0, 1]
- **concerns**: specific dimensions out-of-range
- **recommendations**: concrete actions to fix issues
- **literature_grounding**: papers the LLM relied on

The LLM is deterministic at temperature 0, content-hash-cached, and falls back to `deterministic_fallback()` (verdict=`unknown`) on any failure. Requires `OPENCODE_API_KEY` env var.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Scorer returns `score=0.0` | Missing input files (cohort.json, state.tif) | Ensure the run produced expected artifacts; check `--emit-cohort-log` flag |
| Composite drops to 0.0 | Any single scorer returned `score <= 0.0` | Check which scorer failed; geometric mean zeroes out |
| D6_mass or D7_determinism fail | NaN/Inf in state rasters or non-deterministic seeds | Check for NaN propagation in the engine; verify seed reproducibility |
| D10_perf regression | Rollout took >30s | Profile the engine; check if new features added per-step cost |
| LLM verdict = `unknown` | `OPENCODE_API_KEY` not set or API timeout | Set the env var; check network; the framework continues without LLM |
| `pytest.skip` on full tests | `CALIBRATION_TIER` not set to `full` | Run with `CALIBRATION_TIER=full uv run pytest -m full -v` |

## Related skills

- **abm-engine** — mal-abm-fast C++ engine build, run, and configuration
- **mal-core-api** — stable pipeline logic in mal-core/ (promotion target for stabilised scorers)
