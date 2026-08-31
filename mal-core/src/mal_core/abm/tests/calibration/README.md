# mal-abm-fast — Calibration Test Framework

Pytest-based calibration harness for the **mal-abm-fast** C++ ABM engine
(`mal-core/src/mal_core/abm/`). It scores ABM rollouts against a
multi-dimension scorecard (D1–D24), combines them into a weighted geometric
mean, and compares every run against both the **previous run** and the
**best historical run** (all-time best composite).

> **Two scoring systems live in this repo.** This package is the *test-time*
> calibration harness (pytest, run from this directory). The *post-run*
> scoring pipeline — `malariasim score` writing `scorecard.json` into a run
> dir — lives in `mal-core/src/mal_core/scoring/`. They share scorer concepts
> (and some anchors) but are separate registries.

## Layout

| Path | Purpose |
|---|---|
| `conftest.py` | Fixtures (`cpp_binary`, `ghana_env_path`, `ghana_habitat_path`, `tmp_calibration_dir`) + `fast`/`full`/`llm` marker logic driven by `CALIBRATION_TIER` |
| `thresholds.yaml` | Per-dimension `min_score`, `max_delta`, `hard_floor` + literature sources (single source of truth for scorer thresholds) |
| `scorers/composite.py` | `DEFAULT_WEIGHTS` + weighted geometric mean (handles variable dimensions automatically) |
| `scorers/base.py` | `Scorer` base class + `ScorerResult` |
| `scorers/*.py` | One module per scorer (see table below) |
| `scorers/llm_scorer.py` | LLM judge (LangChain → OpenCode Zen chat, structured `Verdict` via Pydantic) |
| `scorers/prompts/llm_verdict.md` | System prompt for the LLM judge |
| `scorers/best.py` | Tracks the all-time best composite |
| `scorers/diff.py` | Delta report: current run vs previous run AND vs best historical run |
| `scorers/determinism.py` | Bit-for-bit determinism check across seeds |
| `report.py` | Scorecard report generation |
| `run_calibration.sh` | Convenience wrapper for a full calibration run |
| `experiments/` | Experiment registry (registered experiment + runner) |
| `tests/` | Tests of the harness itself |

## Scorers (D1–D24)

Scorer naming: `D<id>_<name>.py` where `<id>` is the next free number
(D17/D18 are reserved/unused). Every scorer must be registered in
`thresholds.yaml` with `min_score`, `max_delta`, and `hard_floor`, and added
to `scorers/composite.py::DEFAULT_WEIGHTS`.

| Dim | Module | Measures |
|---|---|---|
| D1 | `expansion.py` | Spatial expansion speed vs MRR/negative-exp anchors |
| D2 | `mortality.py` | Adult survival |
| D3 | `eip.py` | EIP (extrinsic incubation period) thermal response |
| D4 | `stability.py` | Population stability vs wire.hpp carrying capacity |
| D5 | `spatial.py` | Moran's I spatial autocorrelation |
| D6 | `mass.py` | Mass conservation (no NaN / lost agents) |
| D7 | `determinism.py` | Same seed → same trajectory |
| D8 | `coupling.py` | Human↔vector coupling (birth-at-cell) |
| D9 | `activation.py` | Pluvial-pool activation rule (PLUVIAL_POOL) |
| D10 | `performance.py` | Wall-clock performance budget |
| D11 | `larval_dynamics.py` | Aquatic stage structure (larva/pupa durations) |
| D12 | `D12_host_density.py` | Host density fidelity |
| D13 | `D13_host_seeking_distance.py` | Host-seeking distance distribution |
| D14 | `D14_mobility_conservation.py` | Mobility matrix conservation |
| D15 | `D15_long_horizon_persistence.py` | Long-horizon persistence |
| D16 | `suitability_auc.py` | Habitat suitability AUC (env-driven) |
| D19 | `D19_pool_persistence.py` | Pool persistence lifetimes |
| D20 | `D20_washout_response.py` | Washout response to heavy rain |
| D21 | `D21_spread_rate.py` | Dispersal/spread rate (p50/p90) |
| D22 | `D22_host_clustering.py` | Host clustering |
| D23 | `D23_oviposition_fidelity.py` | Oviposition site fidelity |
| D24 | `D24_urban_productivity_ratio.py` | Urban vs rural productivity guardrail |

## Run

```bash
# From this directory (mal-core/src/mal_core/abm/tests/calibration)
uv run pytest -m fast -v          # PR gate: all fast scorers, 1 seed, 30 days
uv run pytest -m full -v          # 5 seeds, 90 days + LLM verdict (needs OPENCODE_API_KEY)
CALIBRATION_TIER=full uv run pytest          # env-var equivalent of -m full
OPENCODE_API_KEY=sk-... uv run pytest        # enables llm-marked tests
bash run_calibration.sh                      # convenience wrapper
```

Tier semantics (`conftest.py`):

- `CALIBRATION_TIER=fast` (default) — every test not explicitly marked `full` runs; `full`-marked tests are deselected; `llm`-marked tests run only if `OPENCODE_API_KEY` is set.
- `CALIBRATION_TIER=full` — everything runs.

## C++ binary fixture

`cpp_binary` resolves the compiled engine CLI. Build it first:

```bash
malariasim abm --compile
```

> **Binary resolution pitfall**: the wrapper resolves `bin/mal_abm_fast_darwin`
> (inside `src/mal_core/abm/bin/`) **before** `build/src/mal_abm_fast`. After
> any cmake build, copy the fresh binary:
> `cp build/src/mal_abm_fast bin/mal_abm_fast_darwin` — otherwise runs silently
> use the stale binary.

## Rules for adding a scorer

1. Check an existing scorer doesn't already cover the biological feature.
2. Create `scorers/D<next>_<name>.py`.
3. Register in `thresholds.yaml` (`min_score`, `max_delta`, `hard_floor`).
4. Add its weight to `scorers/composite.py::DEFAULT_WEIGHTS`.
5. Run `uv run pytest -m fast -v`; the diff report shows whether the composite
   improved or regressed vs the previous run and vs the all-time best.
6. Never weaken a test or skip a scorer to force a pass.
