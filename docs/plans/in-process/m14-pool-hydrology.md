
# M14 — Pool Hydrology: Accumulation, Evaporation, Threshold Mortality

> **Status**: Full plan (2026-08-10).
>
> **Predecessor**: M1.5 (PLUVIAL_POOL activation rule); M12 (water datasets — composable but not blocking).
>
> **Goal**: Replace the binary rain-threshold activation of PLUVIAL_POOL patches with a continuous water-balance model. Each patch tracks a daily water level (mm) that accumulates from rain and is depleted by temperature-dependent evaporation. Patches become active when water level exceeds the breeding threshold, and inactive when it drops below the dry-out threshold. Larval mortality gains two new drivers: desiccation below the dry-out threshold, and washout above the heavy-rain threshold.

## 1. Problem statement

The current activation rule (`coordinator.cpp:109-111`, `coordinator.py:332`) is binary per-day:

```cpp
if (twi > 8.0f && water_frac > 0.0f && rain > 15.0f) {
    active = true;
}
```

This assumes three things that biology contradicts:

1. **No accumulation.** Two consecutive 15 mm days are treated as two independent events. A real pool deepens: day 1 fills, day 2 adds more water, the pool persists for days after rain stops.
2. **No temperature-driven drying.** Desiccation is a fixed 10%/day for eggs and L1-L2 (`aquatic_cohort_bank.cpp:38, 168`). A 35°C dry day and a 20°C dry day kill at the same rate. Real evaporation is roughly 4-6 mm/day at 30°C and <2 mm/day at 20°C.
3. **No heavy-rain effect.** The 40mm negative correlation is documented in `wire.hpp:148-150` but never coded. A 50 mm cloudburst should wash larvae out of the pool.

The constant `LARVA_DESICCATION_GRACE_DAYS = 5` (wire.hpp:137) exists but is dead code — the desiccation function never consults it. The `days_since_active` field in `mosquito_state.hpp:39` exists but is never incremented.

## 2. Goal

A patch-level water balance per day, per patch:

```
W[t+1] = max(0, W[t] + rain[t] - evap(T[t], W[t]))
```

State transitions:

- `W >= W_BREED` (deep enough for oviposition) → patch `active` for breeding
- `W < W_DRY` (below the wet-tolerance threshold) → patch `dry`, larval desiccation begins
- `rain[t] >= W_WASH` (heavy rain) → washout event

Larval mortality gains two new terms on top of the existing stage / density-dependent rates:

- `desiccation(W, T, days_dry)` — replaces the flat 10%/day
- `washout(W)` — fraction flushed when rain exceeds the washout threshold

Adult mortality is intentionally untouched in this milestone. The user-facing question is about larval mosquito survival, which lives entirely on the aquatic side.

## 3. Design

### 3.1 New constants (wire.hpp)

```cpp
// Pool hydrology (M14).
// All water amounts in mm (same units as CHIRPS daily rainfall).
inline constexpr float POOL_WATER_BREED_MM     = 5.0f;   // min water depth for oviposition
inline constexpr float POOL_WATER_DRY_MM      = 1.0f;   // below this: larvae desiccate
inline constexpr float POOL_WATER_MAX_MM      = 500.0f; // cap to prevent runaway accumulation
inline constexpr float POOL_RAIN_WASH_MM      = 40.0f;  // heavy rain: washout event
inline constexpr float POOL_DESICCATION_GRACE_DAYS = 5; // mirror of LARVA_*, repurposed
inline constexpr float POOL_EVAP_REF_MM       = 5.0f;   // reference evap at 30°C
inline constexpr float POOL_EVAP_REF_T        = 30.0f;  // reference temperature
inline constexpr float POOL_EVAP_T_COEFF      = 0.07f;  // fractional change per °C from ref
inline constexpr float POOL_WASH_FRACTION_MAX = 0.6f;   // at rain=80mm, 60% larvae flushed
inline constexpr float POOL_DESICC_BASE_DAILY = 0.10f;  // baseline desiccation at 30°C, day 6+
```

These are placed in `wire.hpp` next to `PLUVIAL_POOL_RAIN_THRESHOLD_MM` (line 151) and `LARVA_DESICCATION_GRACE_DAYS` (line 137). The old `PLUVIAL_POOL_RAIN_THRESHOLD_MM = 15.0f` is **kept** but **re-interpreted** as the refill threshold: a day with rain > 15 mm refills the pool to at least `W_BREED`. This preserves the M1.5 wire-spec semantics for existing tests while changing the dynamics.

### 3.2 Water-balance update (new module: `pool_hydrology.hpp` / `.cpp`)

A new module in `mal-core/src/mal_core/abm/src/` owns the per-patch daily water state. Pure header-only struct + free functions — no dependency on the ABM engine state.

```cpp
// pool_hydrology.hpp
namespace mal_abm_fast {

struct PoolState {
    float water_mm      = 0.0f;   // current water depth (mm)
    int   days_dry      = 0;      // consecutive days with water < DRY
    int   days_since_fill = 0;    // consecutive days since last rain > REFILL
};

struct DailyForcing {
    float rain_mm    = 0.0f;      // today's daily rainfall (CHIRPS)
    float temp_c     = 25.0f;     // today's mean air temp (ERA5)
};

PoolState advance_pool(const PoolState& prev, const DailyForcing& f);

}  // namespace mal_abm_fast
```

`advance_pool` implements:

```cpp
PoolState advance_pool(const PoolState& prev, const DailyForcing& f) {
    PoolState next;
    // 1. Evaporation — Penman-Monteith simplified, daily (mm/day).
    float evap = POOL_EVAP_REF_MM *
        (1.0f + POOL_EVAP_T_COEFF * (f.temp_c - POOL_EVAP_REF_T));
    if (evap < 0.5f) evap = 0.5f;  // floor: even cold dry days lose some water
    // 2. Water update.
    float w = prev.water_mm + f.rain_mm - evap;
    if (w < 0.0f) w = 0.0f;
    if (w > POOL_WATER_MAX_MM) w = POOL_WATER_MAX_MM;
    next.water_mm = w;
    // 3. Dry-day counter.
    next.days_dry = (w < POOL_WATER_DRY_MM) ? prev.days_dry + 1 : 0;
    next.days_since_fill = (f.rain_mm > POOL_RAIN_THRESHOLD_MM) ? 0 : prev.days_since_fill + 1;
    return next;
}
```

Evaporation model rationale: a single exponential-with-temperature-mean is enough for a daily-step ABM with daily CHIRPS forcing. A full Penman-Monteith needs humidity, wind, and net radiation — none of which are in the current forcing pipeline. The reference value (5 mm/day at 30°C) matches the lower end of published pan-evaporation rates for West Africa (5-8 mm/day in the dry season, Ward 2015). The temperature coefficient (0.07/°C) gives ~3.5 mm/day at 20°C and ~6.5 mm/day at 35°C — consistent with the FAO Penman-Monteith climatology for the Guinea-Sudano zone.

The module is unit-tested in isolation with three fixture cases: stable pool (rain = evap), filling pool (rain > evap), drying pool (rain < evap).

### 3.3 Patch activation rule (coordinator.cpp)

`to_dataframe()` lines 85-141 are extended to maintain a per-patch `PoolState` registry (keyed by `patch_id`). The registry is initialised empty, populated on the first day the patch enters `union_cells`, and persists across days — site fidelity continues to apply.

The activation flag becomes a function of `W`:

```cpp
const bool active = (pool.water_mm >= POOL_WATER_BREED_MM);
```

The pre-existing patches (line 85-97) are no longer unconditionally inserted. They share the same hydrology rule. The comment at line 89-94 ("Pre-existing patches are always activated") is replaced with "Pre-existing patches share the same water-balance rule; permanent water bodies maintain water_mm >= W_BREED because their water_frac is high and TWI > 8."

The `(twi > 8.0f && water_frac > 0.0f)` part of the original rule is kept as a **precondition for hydrology tracking** — cells that don't meet it don't get a `PoolState` allocated and never become active. This preserves the static-terrain filter that prevents random flatlands from being tracked.

### 3.4 Aquatic larval mortality (aquatic_cohort_bank.cpp)

The `desiccation()` function (lines 145-172) is rewritten to use `ps.pool_state`:

```cpp
float desiccation_rate(const PoolState& pool, AquaticStage stage, uint8_t instar) {
    // Only eggs and early instars (L1, L2) are vulnerable — same as before.
    bool vulnerable = (stage == EGG) || (stage == LARVA && instar <= 2);
    if (!vulnerable) return 0.0f;
    if (pool.water_mm >= POOL_WATER_DRY_MM) return 0.0f;  // wet enough
    // Grace period: first N days dry, no mortality.
    if (pool.days_dry <= POOL_DESICCATION_GRACE_DAYS) return 0.0f;
    // After grace: temperature-modulated rate.
    int past_grace = pool.days_dry - POOL_DESICCATION_GRACE_DAYS;
    float ramp = 1.0f - std::exp(-0.3f * past_grace);  // ramps to ~1 over 5 days
    return POOL_DESICC_BASE_DAILY * ramp;
}
```

And a new function `washout()` is called from the daily update loop:

```cpp
float washout_fraction(const PoolState& pool, const DailyForcing& f) {
    if (f.rain_mm < POOL_RAIN_WASH_MM) return 0.0f;
    // Linear from 0 at WASH to WASH_FRACTION_MAX at 2*WASH, capped.
    float excess = (f.rain_mm - POOL_RAIN_WASH_MM) / POOL_RAIN_WASH_MM;
    return std::min(POOL_WASH_FRACTION_MAX, excess * POOL_WASH_FRACTION_MAX);
}
```

`washout_fraction` is applied to egg, larva, and pupa cohorts with a binomial draw — same RNG pattern as `stage_mortality`. Adult washout is **not** modelled in this milestone (mosquitoes are not aquatic; they can shelter).

### 3.5 Python implementation

The Mesa-Geo sim in `mal-ghana-sim` mirrors the C++ logic. New module `mal-ghana-sim/src/mal_ghana_sim/abm/pool_hydrology.py` with the same constants and the same `advance_pool` function. The Python `HabitatPatch` gains a `pool_state` field, initialized to all zeros. `coordinator.py` is updated to call `advance_pool` once per day per patch and to replace the per-day `active_mask` with a `water_level >= W_BREED` check.

The water-level evolution is a deterministic function of `(rain_history, temp_history)` — no per-day RNG involved.

### 3.6 Wire-spec update

`mal-core/src/mal_core/abm/docs/wire-spec.md` line 155 area adds a new section:

```
# Pool hydrology (M14)
POOL_WATER_BREED_MM        = 5.0   # min depth for oviposition
POOL_WATER_DRY_MM         = 1.0   # below this: larvae desiccate
POOL_RAIN_WASH_MM         = 40.0  # heavy rain: washout event
[full list with rationales]
```

The existing `PLUVIAL_POOL_RAIN_THRESHOLD_MM = 15.0` entry remains — it's reused as the refill threshold. A footnote explains the dual role.

### 3.7 Calibration scorers

Two new scorers in `mal-core/src/mal_core/abm/tests/calibration/scorers/`:

**D16 — pool_persistence**. Verifies that a 30 mm rain event produces a pool that stays `active` for at least 4 days with T=25°C, then transitions to `dry` within 7 days at T=32°C. Score = fraction of (a, b) sequence pairs from the literature that match the simulated active/dry windows within ±1 day.

**D17 — washout_response**. Verifies that a 50 mm rain event over an active pool reduces larval density by ≥ 30% within 24 hours (rain day + 1 day). Score = whether the washout draw produces a population drop in the target range.

Both registered in `thresholds.yaml` with `min_score = 0.70`, `max_delta = -0.20`, `hard_floor = 0.30`. Both added to `composite.py::DEFAULT_WEIGHTS` with weight 0.5 each (lower than the geometric-mean default of 1.0 because they test single-event mechanics, not whole-run dynamics).

### 3.8 Scenario extensions

Two new fields in `ClimateConfig` (`mal-core/src/mal_core/scenario.py`):

```python
evaporation_multiplier: float = Field(default=1.0, ge=0.0, le=2.0)
washout_multiplier: float    = Field(default=1.0, ge=0.0, le=2.0)
```

These let the calibration scorer sweep the evaporation rate and washout strength independently — useful for fitting to the 24 larval sites (KG `09b7a8bf-080f-49ac-89a7-d9d1fafca0c5`).

## 4. Why this is M14, not M12

M12 (`docs/plans/in-process/m12-water-datasets.md`) adds water **datasets** — new remote-sensing inputs (HydroLAKES, HydroRIVERS, WorldCover, DSWX-S1). The pool hydrology work uses the existing `water_frac` channel from JRC GSW and the existing `rain` channel from CHIRPS. M12 unlocks richer static water masks, but the dynamic water-balance model is independent of the dataset source. They compose: M14 reads `water_frac` from M12's `load_water_stack()` if present, else from JRC GSW.

## 5. Acceptance criteria

- [ ] `pool_hydrology.hpp` / `.cpp` exists with `PoolState`, `advance_pool`, `desiccation_rate`, `washout_fraction`.
- [ ] All 10 new constants live in `wire.hpp` with rationale comments.
- [ ] `coordinator.cpp` `to_dataframe()` produces a `PoolState` per active patch and uses `water_mm >= W_BREED` for the `activated` flag.
- [ ] `aquatic_cohort_bank.cpp` `desiccation()` uses `desiccation_rate(pool, stage, instar)`; new `washout()` function called from `advance_day()`.
- [ ] Python parity: `pool_hydrology.py` + `HabitatPatch.pool_state` + `coordinator.py` sync.
- [ ] Unit tests: `tests/test_pool_hydrology.cpp` (`fill_pool`, `dry_pool`, `partial_recovery`, `temperature_sensitivity`, `washout_active`, `no_washout_dry`) + `tests/test_pool_hydrology.py` parity.
- [ ] Wire-spec doc updated.
- [ ] D16 and D17 scorers registered, weights in composite.
- [ ] `ClimateConfig` gains `evaporation_multiplier` and `washout_multiplier`.
- [ ] Calibration: `uv run pytest -m fast -v` passes with the new scorers active.
- [ ] KG nodes: `op-m14-pool-hydrology` (Operational), `comp-pool-hydrology` (Component), `pitfall-pool-water-balance-uncalibrated` (Pitfall noting the 0.07/°C coefficient is a literature estimate, not Ghana-specific), `arch-pool-state-per-patch` (Architecture).
- [ ] Cross-references: M13 (daily env NC) — the daily forcing inputs to `advance_pool` are exactly the M13 NC layers; any change to M13's variable naming must be reflected here.

## 6. Files

### New

- `mal-core/src/mal_core/abm/include/mal_abm_fast/pool_hydrology.hpp`
- `mal-core/src/mal_core/abm/src/pool_hydrology.cpp`
- `mal-core/src/mal_core/abm/tests/test_pool_hydrology.cpp`
- `mal-ghana-sim/src/mal_ghana_sim/abm/pool_hydrology.py`
- `mal-ghana-sim/src/mal_ghana_sim/tests/abm/test_pool_hydrology.py`
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D16_pool_persistence.py`
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D17_washout_response.py`

### Modified

- `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` — 10 new constants
- `mal-core/src/mal_core/abm/src/coordinator.cpp` — replace per-day activation with per-patch `PoolState` registry
- `mal-core/src/mal_core/abm/src/aquatic_cohort_bank.cpp` — replace flat desiccation, add washout
- `mal-core/src/mal_core/scenario.py` — `evaporation_multiplier`, `washout_multiplier`
- `mal-ghana-sim/src/mal_ghana_sim/abm/habitat.py` — `pool_state` field on `HabitatPatch`
- `mal-ghana-sim/src/mal_ghana_sim/abm/coordinator.py` — call `advance_pool`, switch to water-level activation
- `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` — D16, D17 entries
- `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py::DEFAULT_WEIGHTS` — D16, D17 weights
- `mal-core/src/mal_core/abm/docs/wire-spec.md` — pool hydrology section
- `docs/specs/abm/spec.md` — note on activation rule change

### Promoted (when stable)

- `pool_hydrology` is a candidate for promotion from `mal-core` to `mal-commonlib` once it has its own tests and is used by both engines. Not part of this milestone.

## 7. Pitfalls to record

1. `pitfall-pool-water-balance-uncalibrated` — the 0.07/°C evaporation coefficient is from FAO Penman-Monteith climatology, not Ghana-specific measurements. It must be flagged as a literature estimate, not local data.
2. `pitfall-pool-dry-out-resets-cohorts` — when a pool dries out below `W_DRY`, the cohort bank does not auto-reset. Larvae in L3-L4 and pupae survive on residual moisture (consistent with Depinay 2004). The new `desiccation_rate` only targets eggs + L1-L2, so this is documented, not a regression.
3. `pitfall-pool-refill-vs-rain-threshold` — the 15 mm threshold is reused for refill semantics. A 14 mm rain day does not refill the pool, but it does add water via the water balance. The two effects are independent; a long dry spell followed by 14 mm days will eventually fill the pool below the breed threshold via accumulation.
4. `pitfall-pool-washout-not-applied-to-adults` — adult mosquitoes are not aquatic. The washout only applies to egg, larva, pupa cohorts. If a future M focuses on rain-driven adult mortality, it must be a separate mechanism (see also the user's earlier question about rain > 15 mm adult mortality).
5. `pitfall-pool-temperature-uses-daytime-mean` — the current pipeline uses ERA5 daily mean air temperature, not water surface temperature. In hot dry weather water surface can be 5-10°C above air mean. This is a known limitation; the calibration scorers will only verify that the model produces *plausible* pool dynamics, not that it matches a specific field measurement.

## 8. Cross-link

| Adjacent plan | Link |
|---|---|
| M12 (water datasets) | composes: M14 reads `water_frac` from M12's `load_water_stack()` if present |
| M13 (daily env NC) | input: the daily (rain, temp) layers feed `advance_pool` |
| M7.2 (gonotrophic cycle) | output: `active` flag now depends on water level, not just rain — gonotrophic oviposition sees hydrology |
| M7.3 (multi-species) | extends: per-species water preferences (e.g. *An. funestus* needs permanent water) can layer on top of `PoolState` |
| Dispersal plans | `days_since_fill` could feed dispersal viability (don't fly to a pool that just flooded — too fresh) |

## 9. Acceptance criteria (milestone-level)

M14 is **done** when all 11 items in §5 are checked and the calibration PR gate (`-m fast`) passes with the new scorers active.

## 10. References

- `papers/spatial-analysis/` — TWI justification (M1.5 baseline)
- `papers/anopheles-dynamics/` — Depinay 2004 (desiccation), Mordecai 2013 (thermal responses)
- `papers/hydrology/` — Ward 2015 (West African pan evaporation), FAO Penman-Monteith climatology
- KG `op-m14-pool-hydrology` (Operational), `comp-pool-hydrology` (Component), `comp-m1-5-pluvial-pool` (predecessor)
- KG `rd-13-5da4` — the current pitfall citing the 40mm correlation as unmodeled
- `docs/plans/in-process/m12-water-datasets.md` — sibling plan on water datasets
- `docs/plans/in-process/m7-3-multi-species.md` — sibling plan on per-species preferences

## 11. Change log

| Date | Author | Change |
|---|---|---|
| 2026-08-10 | supervisor | Full plan drafted. Replaces the per-day binary rain-threshold activation with a per-patch water balance (accumulation + evaporation + threshold mortality). |
