# Calibration Test Framework for the mal-abm-fast C++ ABM

> Status: design — implementation to follow. The framework described here
> is the M7+ calibration harness. It builds on the F1.5 thin-slice engine
> (commit 90517f8, 96/96 ctest) and the F1.e parity contract, and extends
> the validation loop from "the sim runs" to "the sim runs **and produces
> biologically realistic dynamics**".

## 0. Why this exists

The ABM engine at `mal-abm-fast/` is parameterised by 17 biological
constants (see `include/mal_abm_fast/wire.hpp`). A single mis-tuned
constant — e.g. setting `ADULT_DAILY_MORT_BASAL = 0.90` when the actual
math gives `p_d ≈ 0.85` at 27.5 °C — collapses the population within 30
days and silently produces a 0-density state COG. The current
`tests/test_*.cpp` GoogleTest suite is **unit**-level: it tests
`lardeux_p_d(27.5) == 0.85`, but not whether that `0.85` is **the right
value for an An. gambiae s.s. population in Ghana June**. We have no
end-to-end regression that says "this parameter set is biologically
viable".

The calibration test framework closes that gap. Every "experiment"
(defined as a parameter set + a fixed climate/habitat input + a seed
list) produces a **scoring report** with 10 orthogonal dimensions. The
scorecard is compared against a stored baseline and against an LLM
verdict, so the user can see at a glance whether their experiment is
*viable* (matches field MRR, EIP, dispersal literature), *plausible*
(within a configurable delta of the previous calibration), or
*regressed* (fell off the cliff).

## 1. Architecture overview

### 1.1 What is an "experiment"?

An **experiment** is a fully-specified ABM run definition: a parameter
set (the 17 `wire.hpp` constants + any CLI flags), the climate input
(`.tif` or `.nc`), the habitat input (`.gpkg`), the AOI (slug or bbox),
the number of simulation days, the PRNG seed list, and (optionally) the
seeding mode. The experiment is **immutable once defined** — its
parameter hash is part of the report and downstream consumers can
re-run the exact same sim by replaying the hash.

```
Experiment
├── name                  "BASAL_0.90_SIGMA_450"
├── params                { ADULT_DAILY_MORT_BASAL: 0.90, ... }
├── inputs                { env: ".../ghana_jan_env.tif",
│                          habitat: ".../ghana_habitat.gpkg" }
├── aoi                   ghana | (W,S,E,N)
├── n_days                90
├── seeds                 [1, 2, 3, 4, 5]
├── seeding_mode          uniform | random_viable | explicit
└── rollout_index         0..4   (one per seed)
```

A **scoring report** is the JSON output of the framework for one
experiment. It contains: the experiment spec, the per-rollout state
COG paths, the per-dimension statistical scores, the composite score,
the delta vs the chosen baseline, the LLM verdict (if enabled), and a
human-readable markdown render.

### 1.2 Where the scoring tests live

**Path**: `mal-abm-fast/tests/calibration/`. This is a new sub-package
of `mal-abm-fast/tests/`, parallel to the existing `test_*.cpp` ctest
binaries. The directory is **not** a CMake subdirectory — it is a
Python package tested by `pytest`, and it lives next to the C++ tests
so the framework can call into the same C++ binary the C++ tests do.

```
mal-abm-fast/tests/calibration/
├── README.md
├── conftest.py
├── fixtures/                    # small env COG + habitat gpkg
├── baselines/                   # JSON baseline scorecards
├── thresholds.yaml              # per-dimension min_score / max_delta
├── scorers/                     # one file per dimension + llm_scorer
├── experiments/                 # named experiment definitions
├── tests/                       # pytest tests
└── report.py                    # CLI: scorecard → markdown
```

The reason for **pytest** (not more ctest): the scoring logic is
statistical (numpy, rasterio, scipy), the baselines are JSON, and the
LLM subagent call is `subprocess.run` to `opencode run`. All of that is
idiomatic pytest. The 96 existing ctest unit tests stay where they are;
this is an integration-level regression on top.

### 1.3 Test runner

Two entry points, one CI integration:

| Command | What it runs | When |
|---|---|---|
| `pytest mal-abm-fast/tests/calibration -m fast` | 5 deterministic scorers, no LLM, 1 seed, 30 days | every commit (PR gate) |
| `pytest mal-abm-fast/tests/calibration -m full` | all 10 scorers, 5 seeds, 90 days, LLM composite | nightly + on-demand |
| `python -m mal_abm_fast.calibration.cli score --exp exp_default` | ad-hoc scoring of one experiment | dev loop |

The `fast` marker is the PR gate (≤ 60s on a single rollout). The
`full` marker is the deep validation (≤ 5 min for 5 rollouts × 10
scorers, plus the LLM call).

### 1.4 Baseline storage

Each baseline is a JSON file at `mal-abm-fast/tests/calibration/baselines/<name>.json`
with the same shape as a scoring report. Baselines are **git-tracked**
and **content-addressed by the parameter hash**: when a user commits a
new calibration (e.g. `ADULT_DAILY_MORT_BASAL=0.94`), they also commit
the resulting report as `baseline_<descriptor>.json` and bump a
`baselines/index.yaml` pointer that says "the current canonical
baseline is `default`".

Three baseline types:

| Type | Example | Purpose |
|---|---|---|
| `default` | `baseline_default.json` | The shipped `wire.hpp` defaults. Always present. |
| `param_sweep` | `baseline_basal_0.90.json`, `baseline_basal_0.94.json` | One baseline per parameter-set under calibration. Used to compare neighbours on a 1-D sweep. |
| `release` | `baseline_m7_0.json` | The calibrated M7.0 baseline. Used as the "is this still good?" anchor on every commit. |

Baselines are *not* raster files — they are JSON. The state COGs that
back them live under `runs/calibration/<exp_name>_<hash>/` and are
gitignored (regenerable from the experiment spec + the C++ binary).

## 2. Scoring dimensions

Each scorer reads the state COGs of one experiment (one per seed) and
produces a single float in `[0, 1]` plus a dict of diagnostic stats
(for the LLM composite). The composite is the **weighted geometric
mean** of the per-dimension scores (geometric so a 0.0 in any
dimension collapses the composite — the over-correction bug should
produce a composite of 0, not a 0.9).

All targets are pinned in `thresholds.yaml` and cite the source paper
in a `source` key so a future maintainer can verify the literature
match without re-deriving it.

### D1. Expansion radius (dispersal kernel)

| | |
|---|---|
| **Metric** | 90th-percentile great-circle distance from each cell that has density ≥ 0.05 × K_MAX on day 90 to the seed cell, aggregated across 5 seeds. |
| **Target** | Median 1.0–1.4 km (Thomas 2013 negative-exp: 90th = 1.28 km; Costantini 1996: 350–650 m/day over 3 days). |
| **Scoring** | `score = exp(-((r_90_obs − 1.2 km) / 0.4 km)²)` (Gaussian, peak at 1.2 km, σ=0.4 km). |
| **Source** | `papers/anopheles-dynamics/dispersal-kernel-calibration.md` §2 (Thomas 2013). |
| **Catches** | Dispersal kernel too narrow (sigma=300m, pre-commit `f7ddd44`) or too wide (sigma=1000m). |
| **Reuses** | `mal-abm-fast/scripts/visualize_state.py` rasterio reads. |

### D2. Adult daily survival (mortality match)

| | |
|---|---|
| **Metric** | Mean lifespan of an adult cohort. Computed by tracking the unique_id (`uid`) of a cohort of 1,000 adults seeded on day 10 and recording the day each agent's `stage_age` advances beyond the seeded value. Lifespan = day of death − day of birth. Aggregate mean over 5 seeds. |
| **Target** | 8–15 days (mean life at daily survival 0.87 = 1/0.13 ≈ 7.7d; at 0.93 ≈ 14.3d). The literature: Saarman 2019, Midega 2007. |
| **Scoring** | `score = exp(-((l_obs − 11.0) / 4.0)²)`. |
| **Source** | `wire.hpp:73-82` (calibration to 0.80–0.95 range); `dispersal-kernel-calibration.md` §2. |
| **Catches** | The 90517f8 over-correction (mean life 6.7d, score ≈ 0.27). |

### D3. EIP completion rate

| | |
|---|---|
| **Metric** | Fraction of adults at day 30 that have `eip_progress >= EIP_THRESHOLD_GD` (110 GD). Aggregate over 5 seeds. |
| **Target** | 0.20–0.50 at 27–28 °C (Mordecai 2013: Brière EIP curve gives ~11–14d EIP at 25–28 °C; 30d - 11d = 19d as adult, mean life 11d → 19/11 ≈ 1.7 effective cycles; with survival 0.87/day the cumulative probability of an EIP-completing adult is 0.20–0.40). |
| **Scoring** | `score = 1.0 if 0.20 ≤ eip_frac ≤ 0.50 else exp(-((eip_frac − 0.35) / 0.15)²)`. |
| **Source** | `papers/anopheles-dynamics/Mordecai-2013-OptimalTemperatureMalariaTransmission.md` (EIP Brière, 25 °C opt). |
| **Catches** | EIP_BASE_C too high (EIP never completes), EIP_THRESHOLD_GD too high (no infectious adults), or mortality so high that no adult lives long enough to become infectious. |

### D4. Population stability (no extinction, no explosion)

| | |
|---|---|
| **Metric** | `min(n_day_30, n_day_60, n_day_90) / n_day_0` (worst-case collapse ratio) and `max(n_day_X) / n_day_0` (worst-case explosion ratio). |
| **Target** | 0.10 ≤ collapse ≤ 0.80 AND explosion ≤ 5.0. |
| **Scoring** | `score = (collapse_ok + explosion_ok) / 2` where each `_ok` is 1.0 if in range, exp-decay outside. |
| **Source** | Internal — derived from `wire.hpp:80` and the M7.0 calibration commit. |
| **Catches** | Population crash (BASAL=0.90 → 0.85 p_d, mean life 6.7d → extinction), runaway birth loop, NaN-driven collapse. |

### D5. Suitability spatial pattern (Moran's I)

| | |
|---|---|
| **Metric** | Moran's I on band 2 (suitability) of the day-90 state COG, with a queen-contiguity weight. |
| **Target** | 0.20–0.70 (positive spatial autocorrelation: mosquitoes cluster around habitat, not uniformly spread). |
| **Scoring** | `score = 1.0 if 0.20 ≤ I ≤ 0.70 else exp(-((I − 0.45) / 0.20)²)`. |
| **Source** | Pattern observation: Bissett 2026 (heterogeneous landscapes). |
| **Catches** | Adults uniformly spread (no habitat-driven clustering) or all in one cell (degenerate seed). |

### D6. Mass conservation (no NaN, no Inf, no all-zero)

| | |
|---|---|
| **Metric** | Fraction of pixels in band 0 and band 1 of every snapshot that are finite and in [0, K_MAX]. Pixels that are NaN, Inf, or out-of-range count as failures. |
| **Target** | 1.00 (all valid). |
| **Scoring** | `score = n_valid_pixels / n_total_pixels` (across all snapshots × 5 seeds). |
| **Source** | `pitfall-abm-nan-cog-write` (memory graph). |
| **Catches** | NaN temp fallback regression (`pitfall-nan-temp-fallback`), out-of-coverage pixel bugs, integer overflow. |

### D7. Determinism (byte-equal re-runs)

| | |
|---|---|
| **Metric** | Two consecutive runs with the same seed and params produce byte-equal state COG files. (This is already tested at the C++ unit level in `test_engine.cpp`, but the calibration framework re-tests it end-to-end with the env + habitat fixtures.) |
| **Target** | 1.00 (byte-equal). |
| **Scoring** | `score = 1.0 if hash(state_cog_1) == hash(state_cog_2) else 0.0`. |
| **Source** | F1.f milestone in `comp-mal-abm-fast-engine`. |
| **Catches** | Uninitialised memory reads, multi-thread race conditions, environment-variable dependence. |

### D8. Suitability-density coupling

| | |
|---|---|
| **Metric** | Pearson correlation between band 0 (density) and band 1 (suitability) of the day-90 state COG, restricted to pixels with density > 0. |
| **Target** | ≥ 0.30 (post-90517f8 the C1 birth-at-cell fix should make suitability track density). |
| **Scoring** | `score = max(0, min(1, (r − 0.0) / 0.50))` (linear ramp from 0 at r=0 to 1 at r=0.50). |
| **Source** | The C1 fix commit message ("adults that dispersed 500m to a new cell still contributed births to their old birth patch"). |
| **Catches** | A regression of the C1 fix (where band 1 is computed from `patch_id` instead of `(row, col)`). |

### D9. Patch activation rate

| | |
|---|---|
| **Metric** | Mean fraction of dynamic PLUVIAL_POOL cells that activate per day, computed from the daily state COG (band 1 > 0 at a cell counts as "active" for that day). |
| **Target** | 0.05–0.30 (Ghana June: ~1,000–3,000 of 5,873 dynamic cells active per day). |
| **Scoring** | `score = 1.0 if 0.05 ≤ rate ≤ 0.30 else exp(-((rate − 0.15) / 0.10)²)`. |
| **Source** | `wire.hpp:107-118` (PLUVIAL_POOL rule). |
| **Catches** | Rain threshold too high (no dynamic patches activate), water_frac threshold bug, TWI filter leak. |

### D10. Performance (wall time per rollout)

| | |
|---|---|
| **Metric** | Median wall time per rollout in seconds (single rollout, single thread, 90 days Ghana). |
| **Target** | ≤ 30 s. |
| **Scoring** | `score = min(1.0, 30.0 / t_obs)` (1.0 at or under target, decaying above). |
| **Source** | M-perf F1.g target (100 rollouts < 5 min on FT3). |
| **Catches** | A regression that adds a per-day O(n²) loop, a missing early-out, an uninitialised cache. |

The composite is `score_composite = (Πᵢ scoreᵢ^(wᵢ))^(1/Σwᵢ)` with default
weights `w = {D1: 2, D2: 3, D3: 2, D4: 3, D5: 1, D6: 2, D7: 2, D8: 2, D9: 1, D10: 1}` (mortality and stability weighted higher because they catch the
deadliest bugs). A score of 0 in D2 (mortality) or D4 (stability)
**zeroes the composite** regardless of weights — the geometric mean
property.

## 3. Subagent scoring pattern

### 3.1 The LLM's role

The 10 deterministic scorers above are sufficient to catch every
biological-regression bug. The LLM scorer is **not** a replacement —
it is a **qualitative verdict** that reads the per-dimension score
report and the experiment spec, and answers three questions a
deterministic scorer cannot:

1. *Is the pattern of scores consistent with a biologically viable
   experiment, or does it look like the calibration is on the verge
   of collapse?* (Pattern reasoning the LLM is good at, the framework
   is not.)
2. *Which direction should the next calibration sweep go?* (The
   framework reports "D2 score 0.27, BASAL=0.90"; the LLM says "raise
   BASAL to 0.94–0.97 to bring mean life into the 8–15d range".)
3. *Does the experiment's spatial pattern look like real Ghana
   savanna, or like an artefact of the model?* (Visual reasoning the
   LLM is good at; the framework reports Moran's I = 0.42 but cannot
   say whether the underlying raster looks like mosquito habitat.)

The LLM scorer is invoked **once per experiment**, **after** the
deterministic scorers complete. It is the composite (D11 in the
scorecard), not a dimension.

### 3.2 The interface

The test instantiates a `langchain_openai.ChatOpenAI` client pointing
at the OpenCode Zen `chat/completions` endpoint. The LLM is given a
system prompt (the entomology calibration judge's charter, with
embedded reference ranges from Costantini 1996, Saarman 2019, Midega
2007, Mordecai 2013, Depinay 2004) plus a user prompt that embeds the
JSON scoring report. The response is parsed via
`with_structured_output(Verdict)`, which uses the model's tool-calling
or JSON-mode capability to return a typed Pydantic object.

The system prompt template lives at
`mal-abm-fast/tests/calibration/scorers/prompts/llm_verdict.md` and
cites the literature directly: `papers/anopheles-dynamics/dispersal-kernel-calibration.md`
(Thomas 2013, Costantini 1996), `papers/anopheles-dynamics/Mordecai-2013-OptimalTemperatureMalariaTransmission.md`
(EIP Brière), plus Saarman 2019, Midega 2007, and Depinay 2004 for
adult daily survival.

```python
# In mal-abm-fast/tests/calibration/scorers/llm_scorer.py

import hashlib
import json
import os
import pathlib
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

LLM_PROMPT_PATH = pathlib.Path(__file__).parent / "prompts" / "llm_verdict.md"
LLM_TIMEOUT_S = 180
LLM_CACHE_DIR = pathlib.Path(".cache/llm_verdicts")
ZEN_BASE_URL = "https://opencode.ai/zen/v1"


class Verdict(BaseModel):
    """The LLM's calibration verdict, returned as a typed Pydantic object."""

    verdict: Literal["viable", "borderline", "regressed", "collapsed"]
    composite_estimate: float
    concerns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    literature_grounding: list[str] = Field(default_factory=list)


def score_with_llm(
    report: dict,
    *,
    model: str = "minimax-m3",
) -> dict:
    """Return the LLM verdict for a scoring report.

    The verdict is cached by the report's content hash so repeat
    invocations on the same experiment are free. If the LLM call
    fails (network, timeout, parse error), the deterministic
    composite is returned as a fallback (with `fallback: true` flag).
    """
    cache_key = hashlib.sha256(
        json.dumps(report, sort_keys=True).encode()
    ).hexdigest()[:16]
    cache_path = LLM_CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    system_prompt = LLM_PROMPT_PATH.read_text()  # the judge's charter

    client = ChatOpenAI(
        model=model,
        base_url=ZEN_BASE_URL,
        api_key=os.environ["OPENCODE_API_KEY"],
        temperature=0.0,
        timeout=LLM_TIMEOUT_S,
    )
    chain = client.with_structured_output(Verdict)

    try:
        result: Verdict = chain.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(report, indent=2)},
        ])
        verdict = result.model_dump()
    except Exception:
        return deterministic_fallback(report, reason="llm_error")

    cache_path.write_text(json.dumps(verdict))
    return verdict
```

The `--agent supervisor` invocation is replaced with a direct LLM
call. The supervisor's access to the project's skills, knowledge
graph, and tools is **not** needed for this task — the LLM is asked
to judge statistics against embedded reference ranges, not to
explore the codebase. Removing the harness makes the call 3-5x
faster (no OpenCode startup), 5-10x cheaper (no agent overhead), and
deterministic (same input + temperature 0 = same output).

#### Why direct API, not opencode harness?

- **Faster**: 1-3s vs 5-15s (no harness startup)
- **Independent**: works on any Python runner, no OpenCode
  installation required
- **Focal context**: the LLM sees only the system prompt + scoring
  report (~2 KB), not the entire project context
- **Reproducible**: temperature 0 + content-hash cache = same output
  for same input

### 3.3 What the LLM sees (input schema)

The LLM is given the scoring report as a JSON file attached with
`-f` plus a system prompt that describes the schema. The full prompt
template lives at `mal-abm-fast/tests/calibration/scorers/prompts/llm_verdict.md`.
The JSON shape:

```json
{
  "experiment": {
    "name": "BASAL_0.90_SIGMA_450",
    "params": {"ADULT_DAILY_MORT_BASAL": 0.90, "ADULT_DISPERSE_SIGMA_M": 450},
    "n_days": 90, "n_seeds": 5, "aoi": "ghana"
  },
  "scores": {
    "D1_expansion_radius":   {"score": 0.41, "value_km": 0.62, "target_km": 1.2},
    "D2_adult_survival":     {"score": 0.27, "mean_life_d": 6.7, "target_d": "8-15"},
    "D3_eip_completion":     {"score": 0.00, "frac_infectious": 0.04, "target_frac": "0.20-0.50"},
    "D4_population_stable":  {"score": 0.00, "collapse_ratio": 0.05, "explosion_ratio": 1.1},
    "D5_morans_i":           {"score": 0.81, "morans_i": 0.38, "target": "0.20-0.70"},
    "D6_no_nan":             {"score": 1.00, "valid_pixels_frac": 1.0},
    "D7_determinism":        {"score": 1.00, "byte_equal": true},
    "D8_density_coupling":   {"score": 0.74, "pearson_r": 0.37, "target": ">=0.30"},
    "D9_patch_activation":   {"score": 0.62, "activation_rate": 0.11, "target": "0.05-0.30"},
    "D10_performance":       {"score": 0.95, "wall_s": 31.6, "target_s": 30}
  },
  "composite": 0.0,
  "baseline": {
    "name": "default",
    "composite": 0.78,
    "delta_composite": -0.78
  },
  "diagnostics": {
    "n_adults_day_0": 5700000,
    "n_adults_day_30": 280000,
    "n_adults_day_90": 12000,
    "infectious_frac_day_90": 0.04,
    "spatial_extent_km2_day_90": 4200
  }
}
```

The system prompt asks for the response in §3.4's schema and instructs
the LLM to:

1. **Ground in the cited literature** — `papers/anopheles-dynamics/`
   is a directory the LLM can `read` via OpenCode tools.
2. **Compare against the baseline** — the `baseline.delta_composite`
   field tells it whether this is a regression.
3. **Recommend the next calibration step** — what single parameter
   change would most improve the composite?

### 3.4 What the LLM returns (output schema)

```json
{
  "verdict": "viable" | "borderline" | "regressed" | "collapsed",
  "composite_estimate": 0.78,
  "concerns": [
    "D2 (adult survival) is 0.27: mean life 6.7d vs target 8-15d. The mortality model is over-correcting.",
    "D3 (EIP completion) is 0.00: only 4% of adults are infectious at day 90, below the 20-50% range. Cascades from D2."
  ],
  "recommendations": [
    "Raise ADULT_DAILY_MORT_BASAL from 0.90 to 0.94-0.97 (Saarman 2019 mean: 0.87; Midega 2007 range: 0.83-0.95).",
    "Re-run experiment with BASAL=0.95 and confirm D2 score >= 0.70 and D3 score >= 0.20."
  ],
  "literature_grounding": [
    "Saarman 2019 self-marking: 0.87 daily survival (CI 0.83-0.90).",
    "Midega 2007 Kenya coast MRR: 0.83-0.95 daily survival.",
    "Mordecai 2013: EIP Brière optimum at 25°C, 11-14d at 25-28°C."
  ]
}
```

The `verdict` enum:

| Verdict | composite | Meaning |
|---|---|---|
| `viable` | ≥ 0.70 | Ship it. |
| `borderline` | 0.50–0.69 | Calibrate further before shipping. |
| `regressed` | 0.30–0.49 | Composite dropped > 0.20 vs baseline. Revert or fix. |
| `collapsed` | < 0.30 | A core dimension scored 0. Revert immediately. |

The scoring framework parses the JSON block out of the LLM's text
output (the LLM may add prose before/after). The parser looks for the
first `{...}` block that satisfies the schema.

### 3.5 Where the LLM call lives in the pipeline

The LLM call is **only** in the `full` marker (nightly + on-demand).
The `fast` marker (PR gate) skips the LLM call entirely and uses the
deterministic composite. This keeps the PR gate under 60s.

The test pipeline:

```
pytest -m fast
├── Run experiment(s)        # mal_abm_fast run --n-rollouts 1
├── Compute D1..D10          # 10 scorers
├── Composite = geometric mean of D1..D10
└── Assertions: composite >= threshold_composite, no 0-scored dim

pytest -m full
├── Run experiment(s)        # mal_abm_fast run --n-rollouts 5
├── Compute D1..D10
├── Composite (deterministic)
├── D11 = score_with_llm(report)   # ← here
└── Assertions: D11.verdict not "regressed" or "collapsed"
```

### 3.6 Flakiness & timeout

Two layers of fallback (the third layer from the `subprocess.run`
design is no longer needed):

1. **Cache by content hash.** Same experiment spec + same scoring
   report → same verdict. Repeat invocations are free (read from
   `LLM_CACHE_DIR`).
2. **LLM timeout = 180s.** If the `ChatOpenAI` call hangs or the
   network drops, the framework catches the exception and returns
   the deterministic composite as a fallback (with
   `fallback: "llm_error"` in the verdict).

The previous "stricter prompt retry" path is gone: `with_structured_output(Verdict)`
constrains the response to a typed Pydantic object via tool-calling
or JSON-mode, so the response is **always** valid against the
`Verdict` schema. The only failure modes that remain are network /
timeout / API errors, all of which collapse into a single
`except Exception` branch.

The fallback is **always deterministic composite + a "no LLM verdict
available" annotation**, never a synthetic LLM verdict. The user
sees the explicit annotation in the markdown report and can re-run
the experiment with `--force-llm` to re-attempt.

## 4. Delta identification

### 4.1 What is the "delta"?

For each scorer `i`, the delta is:

```
delta_i = score_i(current) - score_i(baseline)
```

The composite delta is the same formula on the composite scores. The
user's `thresholds.yaml` declares two limits per dimension:

```yaml
# mal-abm-fast/tests/calibration/thresholds.yaml
D1_expansion_radius:
  min_score: 0.50
  max_delta: -0.30
D2_adult_survival:
  min_score: 0.50
  max_delta: -0.40
  hard_floor: 0.20  # below this, automatic "collapsed"
# ... etc
```

A scorer "regresses" if `score < min_score` OR `delta < max_delta`.
A scorer "collapses" if `score < hard_floor` (a hard cliff — e.g.
mean life < 3d, population < 1% of init).

### 4.2 Baseline selection

The framework picks the baseline in this order:

1. **Explicit `--baseline NAME`** flag on the test invocation.
2. **The default baseline** (`baselines/default.json`) for unmarked
   tests.
3. **The closest param-sweep neighbour** — if the current experiment's
   parameter hash is `h` and the baselines are `default` (h₀) and
   `basal_0.94` (h₁), and `d(h, h₁) < d(h, h₀)` (Hamming distance on
   the param keys), use `basal_0.94` as the baseline.

The explicit flag is for the calibration workflow ("compare this
BASAL=0.95 run against the BASAL=0.94 baseline"). The default is for
the PR gate. The auto-nearest is for exploratory sweeps.

### 4.3 Where the delta is shown

Three surfaces:

1. **CLI**: `python -m mal_abm_fast.calibration.cli report --exp EXP`
   prints a markdown report to stdout. Pipe to a file for
   `runs/calibration/<exp>_report.md`.
2. **Pytest output**: each scorer's `assert score >= min_score` shows
   up as a normal pytest assertion failure. With `pytest -v`, the
   score, target, and delta are shown in the test summary.
3. **GitHub PR comment**: the optional `--post-pr-comment` flag in the
   `calibration` GitHub Action posts the markdown report as a PR
   comment. (See §5.4.)

### 4.4 Threshold defaults

| | min_score | max_delta | hard_floor |
|---|---|---|---|
| D1 expansion | 0.50 | -0.30 | 0.10 |
| D2 survival | 0.50 | -0.40 | 0.20 |
| D3 EIP | 0.30 | -0.40 | 0.10 |
| D4 stability | 0.70 | -0.20 | 0.30 |
| D5 Moran's I | 0.50 | -0.30 | 0.20 |
| D6 no-NaN | 0.99 | -0.01 | 0.95 |
| D7 determinism | 0.99 | -0.01 | 0.95 |
| D8 coupling | 0.40 | -0.40 | 0.10 |
| D9 activation | 0.40 | -0.40 | 0.10 |
| D10 perf | 0.70 | -0.30 | 0.30 |

D6 and D7 (mass conservation + determinism) are the strictest — they
should never regress because they catch mechanical bugs. The composite
is "shipping-eligible" if **all** scorers are above `min_score` AND
the composite is ≥ 0.70.

## 5. Implementation plan

The framework ships in 4 phases. Each phase is independently useful
and ships behind a feature flag so we can stage the rollout.

### Phase 1: Deterministic statistical tests (no LLM)

**Goal**: 10 scorers + composite + baseline diff + markdown report.

| File | Description |
|---|---|
| `mal-abm-fast/tests/calibration/README.md` | What the framework is, how to run it, the scoring-dimension table. |
| `mal-abm-fast/tests/calibration/conftest.py` | Locates the C++ binary (lifted from `mal-ghana-sim/tests/conftest.py`), provides session-scoped fixtures for `tmp_calibration_dir`, `cpp_binary`, `ghana_env_path`, `ghana_habitat_path`. |
| `mal-abm-fast/tests/calibration/fixtures/build_ghana_jan.py` | Builds the small Jan fixture (env COG + habitat gpkg) used by the fast marker. The full June env is too large for PR-gate tests. |
| `mal-abm-fast/tests/calibration/scorers/base.py` | `Scorer` ABC (one method: `score(experiment, run_dir) -> ScorerResult`), `ScorerResult` dataclass (`score: float`, `diagnostics: dict`, `passed: bool`), `ScoringReport` dataclass (aggregates results from all scorers). |
| `mal-abm-fast/tests/calibration/scorers/expansion.py` | D1. Reads 5 state COGs (one per seed), finds the 90th-percentile distance from each cell with `density > 0.05 * K_MAX` to the seed cell. Returns median over 5 seeds. |
| `mal-abm-fast/tests/calibration/scorers/mortality.py` | D2. The hardest scorer. Reads the daily COGs (--snapshot-every 1), tracks agent `uid` over time. The C++ engine doesn't currently expose per-uid time series — this scorer needs a small CLI flag (`--emit-cohort-log`) to write a `cohort.json` with birth/death days. **Action item: add the flag to `mal-abm-fast/src/main.cpp`**. |
| `mal-abm-fast/tests/calibration/scorers/eip.py` | D3. Reads the cohort log, computes the fraction of uids alive at day 30 with `eip_progress >= 110`. |
| `mal-abm-fast/tests/calibration/scorers/stability.py` | D4. Reads the per-day `n_alive` from the cohort log, computes `min/max/mean` over 90 days. |
| `mal-abm-fast/tests/calibration/scorers/spatial.py` | D5. Reads the day-90 state COG, computes Moran's I on band 2 with queen-contiguity weights (libpysal or a hand-rolled implementation). |
| `mal-abm-fast/tests/calibration/scorers/mass.py` | D6. Walks every snapshot × every seed, counts valid pixels. |
| `mal-abm-fast/tests/calibration/scorers/determinism.py` | D7. Re-runs the experiment with the same seed, byte-compares the state COG. |
| `mal-abm-fast/tests/calibration/scorers/coupling.py` | D8. Computes Pearson r between band 0 and band 1 on the day-90 COG, restricted to density > 0 pixels. |
| `mal-abm-fast/tests/calibration/scorers/activation.py` | D9. Counts cells with `band 1 > 0` per day, aggregates over seeds. |
| `mal-abm-fast/tests/calibration/scorers/performance.py` | D10. Wraps the C++ run with `time.perf_counter`, reports wall time per rollout. |
| `mal-abm-fast/tests/calibration/scorers/composite.py` | Geometric mean of D1..D10 with the weight vector. Returns 0 if any scorer is 0. |
| `mal-abm-fast/tests/calibration/experiments/experiment.py` | `Experiment` dataclass (name, params, inputs, aoi, n_days, seeds, seeding_mode). `run(experiment, output_dir) -> RunResult` shells out to the C++ binary and collects COG paths. |
| `mal-abm-fast/tests/calibration/experiments/registry.py` | `EXPERIMENTS = {"default": exp_default, "basal_0.90": exp_basal_0.90, ...}`. |
| `mal-abm-fast/tests/calibration/baselines/default.json` | The shipped baseline. Built by running `exp_default` once, scoring it, and committing the report. |
| `mal-abm-fast/tests/calibration/thresholds.yaml` | The per-dimension limits in §4.4. |
| `mal-abm-fast/tests/calibration/tests/test_default_experiment.py` | The fast-marker PR-gate test. Runs `exp_default`, scores it, asserts composite ≥ 0.70. |
| `mal-abm-fast/tests/calibration/tests/test_basal_sweep.py` | The full-marker calibration-sweep test. Runs `exp_basal_0.90`, `exp_basal_0.94`, `exp_basal_0.97`, asserts D2 score trends up. |
| `mal-abm-fast/tests/calibration/tests/test_delta_from_baseline.py` | Runs `exp_default`, compares to `baselines/default.json`, asserts `|delta| < max_delta` for each scorer. |
| `mal-abm-fast/tests/calibration/report.py` | CLI: `python -m mal_abm_fast.calibration.cli report --exp EXP` renders the markdown report. `python -m mal_abm_fast.calibration.cli diff --exp A --baseline B` shows the delta. |

**Estimated LoC**: ~1,200 LoC Python. ~50 LoC C++ (the `--emit-cohort-log` flag).

> **Note**: Phase 3 adds `scorers/score.py`, `scorers/diff.py`, and `scorers/best.py` for the scorecard runner and dual-delta reporting. These are separate from the Phase 1 `report.py` (the markdown report renderer).

### Phase 2: LLM scorer integration

**Goal**: D11 verdict via a direct `langchain_openai.ChatOpenAI` call
to the OpenCode Zen `chat/completions` endpoint, with content-hash
cache and a deterministic-composite fallback.

| File | Description |
|---|---|
| `mal-abm-fast/tests/calibration/scorers/llm_scorer.py` | The `score_with_llm` function in §3.2: `ChatOpenAI` + `with_structured_output(Verdict)`, content-hash cache, deterministic-composite fallback. One module, one client. |
| `mal-abm-fast/tests/calibration/scorers/prompts/llm_verdict.md` | The system prompt template (the entomology calibration judge's charter). Embeds reference ranges from Costantini 1996, Saarman 2019, Midega 2007, Mordecai 2013, Depinay 2004 and cites `papers/anopheles-dynamics/dispersal-kernel-calibration.md` and `papers/anopheles-dynamics/Mordecai-2013-OptimalTemperatureMalariaTransmission.md`. |
| `mal-abm-fast/tests/calibration/tests/test_llm_scorer.py` | Unit test for the LLM scorer with a mock `ChatOpenAI` client. Verifies cache hit, exception fallback, Pydantic validation against the `Verdict` schema. |
| `mal-abm-fast/tests/calibration/tests/test_full_pipeline.py` | End-to-end test: 5 seeds, 90 days, LLM composite. Marked `slow` so it does not run on PR. |

**Dependencies**: 1 runtime dep (`langchain-openai`, which pulls
`pydantic` transitively). No more `subprocess` plumbing, no more
custom JSON parsers.

**Estimated LoC**: ~250 LoC Python (down from ~400 for the
`subprocess.run` design — the harness mocking, retry logic, and
text-output JSON parser are all gone). The prompt template is ~80
lines of markdown.

### Phase 3: Scorecard runner + delta reporting

**Goal**: every run produces a scorecard; diff shows improvement/regression vs previous run AND vs best historical run.

| File | Description |
|---|---|
| `mal-abm-fast/tests/calibration/scorers/score.py` | CLI: `python -m scorers.score --run-dir <path>` — runs all 10 scorers on a run directory, produces `scorecard.json`. Called automatically by pytest after scoring. |
| `mal-abm-fast/tests/calibration/scorers/diff.py` | CLI: `python -m scorers.diff scorecard_a.json scorecard_b.json` — renders a markdown table showing per-dimension delta + composite delta + status (improved/regressed/unchanged). |
| `mal-abm-fast/tests/calibration/scorers/best.py` | Tracks the best historical scorecard. After each run, compares current composite vs `best_scorecard.json`. If current is better, updates the best. Stores in `runs/calibration/best_scorecard.json`. |
| `mal-abm-fast/tests/calibration/scorers/__init__.py` | Updated to export `score`, `diff`, `best` modules. |

**Scorecard JSON shape** (same as the LLM scorer input):
```json
{
  "experiment": {"name": "...", "params": {...}, "n_days": 90, "n_seeds": 5},
  "scores": {"D1_expansion": {"score": 0.82, "value": 1.15, "target": "1.0-1.4 km"}, ...},
  "composite": 0.78,
  "timestamp": "2026-07-22T15:30:00",
  "run_dir": "/tmp/abm_run_001/"
}
```

**Delta comparison** (dual):
- `delta_prev`: current score vs previous run's score (same experiment, different params/code)
- `delta_best`: current score vs best historical score (all-time best composite)

The diff report shows both:
```markdown
# Delta Report: run_002 vs run_001 (and vs best)

| Dim        | run_001 | run_002 | Best  | Δ prev | Δ best | Status |
|------------|---------|---------|-------|--------|--------|--------|
| D2 survival| 0.73    | 0.81    | 0.85  | +0.08  | -0.04  | ✅ prev / ⚠️ best |
| Composite  | 0.71    | 0.78    | 0.82  | +0.07  | -0.04  | ✅ prev / ⚠️ best |
```

**Best scorecard tracking**:
- `best_scorecard.json` is stored in `runs/calibration/` (gitignored, local only)
- After each scoring run, `scorers/best.py` compares current composite vs best
- If current > best, updates the best file
- The best scorecard is never overwritten with a worse result
- This prevents losing sight of the all-time best when iterating

**Estimated LoC**: ~250 LoC Python.

### Phase 4: Not needed (local workflow)

Phase 4 (CI integration via GitHub Actions) is **not needed** for the current
workflow. The quality gate is local: agents run `pytest -m fast` before proposing.
The calibration tests serve as a living regression battery — every change is
scored, and the diff shows improvement vs the previous run and vs the best
historical run.

If CI is needed in the future, the Phase 4 YAML files can be added at that point.

## 6. Worked example: the 90517f8 over-correction

The user just committed `90517f8` (the biological calibration batch).
The framework would catch the BASAL=0.90 over-correction as follows.

### Input

```
Experiment: BASAL_0.90_SIGMA_450
params:
  ADULT_DAILY_MORT_BASAL: 0.90
  ADULT_DISPERSE_SIGMA_M: 450
  ADULT_DISPERSE_MAX_M: 2000
  ADULT_DISPERSE_PROB: 0.10
  EIP_BASE_C: 16
  EIP_THRESHOLD_GD: 110
  K_MAX: 1000
  BIRTH_FECUNDITY: 0.10
  (other defaults)
aoi: ghana
n_days: 90
seeds: [1, 2, 3, 4, 5]
seeding_mode: uniform
```

### Execution

```bash
cd mal-abm-fast
pytest tests/calibration -m full -v
```

The fast marker alone takes ~45s. The full marker adds ~4 min for 5
seeds and a 180s LLM timeout. Total: ~5.5 min.

### Per-dimension scores

| Dim | Metric | Value | Target | Score | Status |
|---|---|---|---|---|---|
| D1 expansion | 90th-pct distance, day 90 | 0.62 km | 1.0–1.4 km | 0.41 | REGRESSED |
| D2 survival | mean adult life | 6.7 d | 8–15 d | 0.27 | **COLLAPSED** |
| D3 EIP | infectious frac, day 30 | 0.04 | 0.20–0.50 | 0.00 | **COLLAPSED** |
| D4 stability | collapse ratio | 0.05 | 0.10–0.80 | 0.00 | **COLLAPSED** |
| D5 Moran's I | spatial autocorr, day 90 | 0.38 | 0.20–0.70 | 0.81 | OK |
| D6 no-NaN | valid pixels frac | 1.00 | 1.00 | 1.00 | OK |
| D7 determinism | byte-equal rerun | yes | yes | 1.00 | OK |
| D8 coupling | Pearson r | 0.37 | ≥ 0.30 | 0.74 | OK |
| D9 activation | daily activation rate | 0.11 | 0.05–0.30 | 0.62 | OK |
| D10 perf | wall per rollout | 31.6 s | ≤ 30 s | 0.95 | OK |
| **Composite** | | | | **0.00** | **COLLAPSED** |

The composite is **0.00** because D2, D3, D4 are all 0.00 (the
geometric mean zeroes out). The verdict is `"collapsed"`.

### LLM composite

```json
{
  "verdict": "collapsed",
  "composite_estimate": 0.05,
  "concerns": [
    "D2 (adult survival) is 0.27: mean life 6.7d vs target 8-15d. The mortality model is over-correcting — p_d at 27.5°C is 0.85, not 0.90.",
    "D3 (EIP completion) is 0.00: only 4% of adults are infectious at day 90. Cascades from D2 — most adults die before EIP completes.",
    "D4 (population stability) is 0.00: 5% of init pop at day 90. The cascade is mechanical — too few adults → too few births → extinction spiral."
  ],
  "recommendations": [
    "Raise ADULT_DAILY_MORT_BASAL from 0.90 to 0.94-0.97. Saarman 2019 self-marking: 0.87 daily survival. Midega 2007 Kenya coast: 0.83-0.95. The current 0.90 is on the conservative end and gives p_d = 0.85 at 27.5°C.",
    "Re-run with BASAL=0.95 and confirm D2 score >= 0.70, D3 score >= 0.20, D4 score >= 0.70."
  ],
  "literature_grounding": [
    "Saarman 2019 self-marking: 0.87 daily survival (CI 0.83-0.90).",
    "Midega 2007 Kenya coast MRR: 0.83-0.95 daily survival.",
    "Costantini 1996 Burkina Faso savanna: 0.80-0.88 daily survival.",
    "Mordecai 2013: EIP Brière optimum at 25°C, 11-14d at 25-28°C."
  ]
}
```

### Markdown report

```markdown
# Calibration Report — BASAL_0.90_SIGMA_450

**Composite**: 0.00 / 1.00
**Verdict**: :red_circle: COLLAPSED
**Baseline**: default (composite 0.78, delta -0.78)
**Date**: 2026-07-22
**Duration**: 5m 24s (5 seeds × 90 days + 162s LLM)

## Per-dimension scores

| Dim | Score | Status | Metric | Target |
|---|---|---|---|---|
| D1 expansion radius | 0.41 | REGRESSED | 0.62 km | 1.0-1.4 km |
| D2 adult survival | 0.27 | **COLLAPSED** | 6.7 d | 8-15 d |
| D3 EIP completion | 0.00 | **COLLAPSED** | 0.04 | 0.20-0.50 |
| D4 pop stability | 0.00 | **COLLAPSED** | 0.05 | 0.10-0.80 |
| D5 Moran's I | 0.81 | OK | 0.38 | 0.20-0.70 |
| D6 no-NaN | 1.00 | OK | 1.000 | 1.000 |
| D7 determinism | 1.00 | OK | yes | yes |
| D8 density-suit | 0.74 | OK | 0.37 | >= 0.30 |
| D9 activation | 0.62 | OK | 0.11 | 0.05-0.30 |
| D10 performance | 0.95 | OK | 31.6 s | <= 30 s |

## LLM verdict

> :red_circle: **COLLAPSED** — composite 0.05
>
> The mortality model is over-correcting. p_d at 27.5°C is 0.85, not 0.90. Mean adult life 6.7d vs 8-15d target.
>
> **Fix**: raise ADULT_DAILY_MORT_BASAL from 0.90 to 0.94-0.97. Re-run with BASAL=0.95.
>
> Sources: Saarman 2019, Midega 2007, Mordecai 2013.
```

### How this would have caught the bug

The user would have seen the COLLAPSED verdict **before merging**
because the `calibration-fast.yml` GitHub Action runs on every PR. The
LLM composite would have posted the recommendation to raise
`ADULT_DAILY_MORT_BASAL` to 0.94-0.97, and the deterministic scorers
would have flagged D2, D3, D4 with explicit metric values. The user
could have either:

1. Bumped `BASAL` to 0.95 in the same PR (the LLM recommendation
   gives them a target), or
2. Asked the LLM to suggest an alternative fix (e.g. raise
   `ADULT_MORT_CAP` from 0.95 to 0.97, or lower `ADULT_SIGMA` from
   7 to 9 to broaden the curve).

Either way, the **silent population collapse** is now a
**visible composite=0.00** before merge.

## 7. Open questions

### 7.1 Stochasticity

The C++ engine is deterministic given a seed, but two seeds produce
two different runs. How do we score an experiment that is itself a
distribution?

**Proposed answer**: every scorer's `score()` method takes a
`List[Path]` of state COGs (one per seed) and returns the **median
across seeds** for the value, with the IQR as a diagnostic. The score
function still operates on a single value, so the test is
deterministic. The IQR shows up in the markdown report so the user
can see "D1 score 0.41, IQR 0.18 — this is a noisy dimension, more
seeds would help".

For the composite, we use the median of the per-seed composites, not
the composite of medians, so a single bad seed doesn't zero out the
composite.

### 7.2 Speed

90 days × 5 seeds = 450 ABM days. The fast marker (1 seed, 30 days)
is the PR gate at ~45s. The full marker (5 seeds, 90 days) is ~4 min
plus the LLM call. We can speed this up by:

1. **Snapshotting less frequently** — `--snapshot-every 5` (18
   snapshots instead of 90). This reduces the D2 mortality scorer's
   cohort-log size by 5x.
2. **Running seeds in parallel** — the C++ engine already has
   `--n-rollouts`. The framework wraps this and just needs to collect
   the per-rollout COGs.
3. **Caching the ABM run by experiment hash** — if the experiment
   spec + the C++ binary hash are unchanged, reuse the COGs from
   `runs/calibration/<exp>_<hash>/`. The cache is invalidated when
   either changes.

### 7.3 LLM grounding

The LLM is asked to ground its verdict in the literature. Three
options:

1. **Hardcoded targets** (current design). The `thresholds.yaml` file
   cites papers in the `source:` key. The LLM is told "the literature
   targets are listed in thresholds.yaml" and is expected to find the
   paper files via OpenCode's `read` tool. **Pro**: explicit, auditable.
   **Con**: thresholds.yaml can drift from the actual literature.
2. **Knowledge graph at runtime** (future). The LLM queries
   `memory_recall` for "adult survival An. gambiae s.s. Ghana" and
   gets back the relevant paper nodes + Pitfall nodes. **Pro**: always
   current. **Con**: requires the KB to have the right nodes (we have
   `pitfall-overcommit-abm` and `pat-cesga-exec-workflow` but no
   paper-summary nodes yet).
3. **Hybrid** (recommended). Thresholds.yaml is the source of truth
   for **scoring**; the LLM also queries the KB for **recommendations**
   ("what does our Pitfall knowledge say about BASAL over-correction?").

We start with option 1 (hardcoded) and graduate to option 3 as the KB
grows.

### 7.4 Should the LLM see the code diff?

The framework passes the scoring report to the LLM by default. The
`--include-code-diff` flag adds `git diff <baseline_commit>..HEAD` to
the prompt. **Trade-off**:

- **With diff**: the LLM can say "the regression is in
  `mosquito_submodel.cpp:lardeux_p_d` — the `p < 0.60` clamp is
  wrong". Faster root cause.
- **Without diff**: the LLM treats the experiment as a black box, so
  the verdict is invariant to which code change caused the regression.
  Better for "is this calibration viable?" questions.

**Recommended default**: `--include-code-diff` on for `pytest -m full`
(so the LLM can help debug), off for the PR-gate `pytest -m fast`
(which has no LLM anyway).

### 7.5 What about the Python ABM (`mal-ghana-sim`)?

The framework is written for `mal-abm-fast` because that's the
production engine. The Python ABM in `mal-ghana-sim/` is a research
reference. Two options:

1. **Skip the Python ABM.** The calibration framework only scores
   the C++ engine. The parity test (`test_abm_fast_parity.py`) is the
   contract between them.
2. **Score the Python ABM too.** Useful for catching "Python ABM
   regression" bugs that the parity test misses (e.g. a Python ABM
   bug that produces the same wrong answer as the C++ engine).

**Recommended**: start with option 1. The Python ABM is not under
active calibration — it's a reference. If the user later wants to
calibrate against the Python ABM's outputs, that's a new experiment
class (`experiment_type="python_reference"`) and a new scorer
(`scorers/parity.py` that compares Python and C++ outputs).

### 7.6 What if the env COG is too big for the PR gate?

The Ghana June env COG is ~50 MB. The fast marker (1 seed, 30 days,
Ghana Jan) uses a smaller fixture. The full marker (5 seeds, 90 days,
Ghana June) needs the full env. The CI workflow caches the env COG
in `~/.cache/malaria-sentinel/envs/` keyed by content hash.

### 7.7 What's the LLM cost?

Each `score_with_llm` call is one direct API request to the OpenCode
Zen `chat/completions` endpoint. The `minimax-m3` model is the
project's default. The total prompt is ~1.5 KB (the system prompt
charter + the JSON scoring report) and the structured response is
~500 tokens.

At OpenCode Zen's published `minimax-m3` pricing (~$0.30/M input
tokens, ~$1.20/M output tokens, ~$0.06/M cached-read tokens) the
per-call cost is **~$0.001** (a tenth of a cent). The content-hash
cache makes re-runs of the same experiment effectively free, and a
~80% cache-hit rate at the nightly cadence is realistic (each
nightly run re-evaluates 1-2 fresh experiments out of 30+).

The LLM call is **only** in `pytest -m full`, which runs nightly and
on-demand — not on every commit. So the LLM cost is **~$0.03/month**
at nightly cadence.

## 8. Acceptance criteria

The framework is "shipped" when:

| Criterion | Metric | Target |
|---|---|---|
| All 10 scorers pass on `exp_default` | composite ≥ 0.70 | yes |
| LLM composite verdict on `exp_default` is `"viable"` or `"borderline"` | manual review | yes |
| Re-running `exp_default` produces a byte-equal scoring report (D7) | hash diff | 0 |
| Re-running `exp_default` 5x produces 5 byte-equal scoring reports | hash diff | 0 |
| LLM call timeout fallback returns deterministic composite | unit test | pass |
| LLM call parse-error fallback returns deterministic composite | unit test | pass |
| CI fast marker runs in < 60s | wall time | pass |
| CI full marker runs in < 6 min | wall time | pass |
| The 90517f8 BASAL=0.90 experiment is scored as `"collapsed"` | manual reproduction | pass |
| Phase 3 works | `python -m scorers.score --run-dir <path>` produces scorecard.json | pass |
| Phase 3 diff works | `python -m scorers.diff a.json b.json` produces markdown table | pass |
| Phase 3 best tracking | best_scorecard.json updates when composite improves | pass |

When all 9 are green, the framework is the M7+ regression anchor and
replaces the current "eyeball the GIF" workflow.
