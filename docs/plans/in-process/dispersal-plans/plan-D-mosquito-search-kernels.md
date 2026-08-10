# Plan D — Mosquito Search Kernels (Host + Oviposition)

| Field | Value |
|---|---|
| **Plan ID** | D |
| **Status** | proposed |
| **Supersedes** | Plan B (host-seeking) — extends with kernel fix + patch tracking + oviposition kernel |
| **Hypothesis** | The current ABM models only the **sensing** half of mosquito search (compute_attraction) and discards both the **direction** (approach_vector is dead code) and the **biological range** (35m scale is below detection thresholds). Additionally, oviposition-site-seeking uses random walk + binary site check, which contradicts literature showing gravid females actively follow water-vapour and VOC plumes. Fixing both kernels, wiring directed flight, and correcting the structural `patch_id` bug produces a realistic, biologically anchored spatial signature. |
| **Risk class** | Medium — touches the state machine, kills two dead-code paths, adds a new kernel class, modifies egg deposition semantics. |
| **Effort** | ~5 sessions |
| **Owner (TBD)** | `wt/plan-d-mosquito-search` → branch `common/abm-plan-d` |
| **Branch prefix** | `common/abm-plan-d` |

---

## 1. Why Plan D exists (motivation)

Three independent investigations (re-read at session-start, see AGENTS.md) converge on a single diagnosis:

### 1.1 Host-seeking range is too short

| What the code does | What the literature says |
|---|---|
| `kScale = 35m` (CO₂ plume decay constant, `host_seeking.cpp:35`) | CO₂ + body odour detected up to **~60–100m** (Giraldo 2023, Okumu 2013); attraction significant at **70m** (Okumu 2013); **94% malaria reduction** when habitats within **300m** of houses are eliminated (Yang 2009). |
| `search_radius_m = 70m` (default, `host_seeking.hpp:73`) | Short-range host-seeking window is **30–300m** (`dispersal-kernel-calibration.md` §6). |
| `D13_host_seeking_distance.py` validates `[20–70m]` | The scorer **enforces** the bug instead of detecting it. |

**Consequence**: the ABM's `compute_attraction` is biologically off by **~10×** for short-range host-seeking. Females within realistic CO₂-plume reach of a village get `attraction ≈ exp(-d/35)` — a mosquito 100m from a household receives **5.6%** of the maximum, and at 200m receives **0.31%**. Yang 2009 shows that 94% of transmission is mediated by mosquitoes within 300m of a house — this range is invisible to the current kernel.

### 1.2 Directed flight is implemented but never called

`HostSeekingModel::approach_vector` is fully implemented at `host_seeking.cpp:171` with a clear docstring ("directional step toward target, clamped to step_size_m"). `GonotrophicState::HOST_APPROACH` is declared at `gonotrophic_cycle.hpp:25-37` but the `mosquito_submodel.cpp` gonotrophic loop at lines 434–519 has no `case HOST_APPROACH:` branch. Females diffuse randomly via the daily local-Gaussian dispersal kernel (σ=450m, prob=0.05) regardless of whether a host is detected.

This is the **sensing-without-direction** defect called out by Depinay 2004, Plan B, and the existing `approach_vector` docstring.

### 1.3 Oviposition-site-seeking uses random walk + binary check

The `OVIPOSITION_SEEKING` state at `mosquito_submodel.cpp:448-482` does:
1. Scan `patch_states` for an activated patch matching the agent's current `(row, col)`.
2. If found → transition to `OVIPOSITING`.
3. If not found → stay in `OVIPOSITION_SEEKING` for another day of random-walk dispersal.

**Literature says otherwise** (Okal 2013, Lindh 2015, Mwingira 2020, *Malaria Journal* 2021 review):
- Gravid *An. gambiae* follow **water-vapour plumes** over several metres (Okal 2013 demonstrated ≥5m).
- They are attracted to **volatile organic compounds** (cedrol, nonane, 2,4-pentanedione) emitted from soil/grass/larval water at **9+m** (Lindh 2015, semi-field).
- They use **visual cues** (polarised light from water surfaces, near-IR heat plumes) at long range.

The current model is structurally equivalent to a hungry mosquito that smells CO₂ but walks randomly until it happens to find a house. It works in dense landscapes; it collapses in sparse ones.

### 1.4 The structural `patch_id` bug

Independent of the kernel defects, the model has a **data-flow bug** that all three dispersal mechanisms (local Gaussian, windborne, future directed flight) inherit:

```
[dispersal]              mosquito lands at cell X (X ≠ natal)
[OVIPOSITION_SEEKING]    → finds water at X  ✓
[OVIPOSITING]            → cohort_bank_.add_eggs(soa_.patch_id[si], N)
                                              ↑ never updated
                                              = natal patch_id (source)
```

Eggs materialise in the **source** patch, not the destination. For local Gaussian (σ=450m) the bug is invisible. For windborne (potentially 10s of km) it produces systematic misallocation. Plan B extending directed flight to 2km would make the bug user-visible.

### 1.5 Plan C is not warranted by literature

Diallo 2026 (12,937 *An. gambiae* s.l., DNA-tagged continuous MRR, Mali, Sept-Dec 2019): **70% of recaptured mosquitoes in a different zone from release** (r=0.97, P<0.001). The paper states explicitly "**no site fidelity**" for feeding, resting, or oviposition sites. Plan C's `natal_patch_id` + 70%-return walk is **not biologically supported**. Plan D's patch-tracking fix achieves the same correctness goal (eggs land in destination, not source) by updating `patch_id` on position change — without inventing a return mechanism that field data rejects.

---

## 2. Biological hypothesis

**H₁ (host-seeking range)**: Increasing the kernel scale from 35m → 100m (CO₂ + body-odour plume, anchored on Giraldo 2023 and Spitzen 2013) and the search radius from 70m → 300m (Yang 2009) raises D13 above 0.75 and D1 (expansion) above 0.70 because the simulated females can now reach villages within realistic short-range host-seeking windows.

**H₂ (directed flight)**: Wiring `approach_vector` into a new `HOST_APPROACH` state, gated on `detect_host_cell(range_m=2000)` finding a target, replaces isotropic random walk with appetitive upwind flight along detected plumes. Produces clustered village-attraction (Plan B's signature) and satisfies the Thomas 2013 p90 = 1.67 km / p95 = 2.83 km targets via directed component (200–400 m/day) without inflating long tail.

**H₃ (oviposition kernel)**: Adding a parallel `OvipositionSeekingModel` with water-vapour scale 50m + 500m search radius (Okal 2013, Lindh 2015) and a `OVIPOSITION_APPROACH` directed walk replicates the literature-documented gravid-female plume-following behaviour and replaces the random walk + binary check.

**H₄ (patch tracking)**: Updating `soa_.patch_id[si]` whenever the agent's `(row, col)` changes (HOST_APPROACH arrival, windborne landing, local dispersal, oviposition arrival) closes the structural egg-misallocation bug. Combined with no-site-fidelity (Diallo 2026), this treats `patch_id` as "current home patch" rather than "natal patch" — a simpler model that matches field data better than Plan C.

**H₅ (starvation pressure)**: Adding a 7-day starvation timer on `HOST_SEEKING` and `HOST_APPROACH` (start 7, decrement only if D1 remains high) prevents unrealistic indefinite search in sparse landscapes without collapsing the adult population.

---

## 3. Literature basis

| Source | File | Key numbers / claims |
|---|---|---|
| **Giraldo et al. 2023** (Current Biology) | `papers/perplexity-investigations/` (add link on import) | CO₂ plume detection up to ~60m; body odour > CO₂ for long-range; semi-field Zambia. |
| **Okumu et al. 2013** (Parasites & Vectors) | (add on import) | Taxis boxes: CO₂ attracts significantly at 70m; activates at 100m. |
| **Yang et al. 2009** (Malar J) | `papers/anopheles-dynamics/dispersal-kernel-calibration.md` §6 | Eliminating habitats within **300m of houses reduced malaria by 94%** — anchors D13 MAX. |
| **Spitzen et al. 2013** | (cited in dispersal-kernel-calibration.md) | An. gambiae responds to CO₂ at 60–70m in low-wind nocturnal conditions. |
| **Costantini et al. 1996** | `papers/anopheles-dynamics/costantini-1996-...md` | 350–650 m/day net displacement (directed + passive); 35m CO₂ baseline. |
| **Thomas et al. 2013** (PLOS ONE) | `papers/anopheles-dynamics/thomas-2013-...md` | p90 1.28 km, p95 1.67 km; p95 half-Cauchy 2.83 km. Anchors D16. |
| **Depinay et al. 2004** | `papers/anopheles-dynamics/depinay-2004-...md` | Active host-seeking flight along plumes — supports directed (non-random) walk. |
| **Okal et al. 2013** (Malar J) | (add on import) | Water vapour pre-oviposition attractant; ≥5m in semi-field; "navigate through the landscape". |
| **Lindh et al. 2015** (Malar J) | (add on import) | Cedrol attracts gravid females at **9+m** in semi-field; 84% trap rate with soil infusion. |
| **Mwingira et al. 2020** (J Chem Ecol) | (add on import) | Nonane, 2,4-PD attractants; DMDS/DMTS repellents; larval-stage infochemicals. |
| **Herrera-Varela et al. 2014** (Malar J) | (add on import) | Soil infusion attracts 2× over lake water alone; chemical cues. |
| **Diallo et al. 2026** (bioRxiv, Mali MRR) | (add on import) | **70% recaptured in different zone from release** (r=0.97). "No site fidelity" for feeding, resting, oviposition. |
| **Epopa et al. 2017** (Parasites & Vectors) | (add on import) | Male dispersal 40–549m over 7 days; release location explains 44% of variance. |
| **Saarman et al. 2019** (Malar J) | `papers/anopheles-dynamics/saarman-2019-...md` | Mean dispersal 579m (CI 521–636). |

### Anchor summary

- **kScale = 100m** (Giraldo 2023 + Spitzen 2013 + Okumu 2013 ceiling): CO₂ + body odour plume.
- **search_radius = 300m** (Yang 2009): 94% reduction threshold.
- **detect_host_cell range = 2000m** (Plan B): matches 2km threshold for transition from random walk to directed flight.
- **step_size = 50m** (existing default): one grid-cell step per day; matches Thomas 2013 first-flight MDT.
- **OVIPOSITION kScale = 50m** (Okal 2013: water vapour plume decay); **search_radius = 500m** (Okal 2013: water vapour travels in wind; Lindh 2015: 9+ m semi-field scaled up).
- **starvation timer = 7 days** start; tune down to 5 if D1 remains high.
- **dispersal constants unchanged** (`ADULT_DISPERSE_SIGMA_M = 450m`, `ADULT_DISPERSE_PROB = 0.05`, `ADULT_DISPERSE_MAX_M = 2000m`).

---

## 4. Code changes

### Phase 1 — Kernel host-seeking expansion

**File**: `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp`

Add new constants near the host-seeking block (lines 35-45):

```cpp
// Host-seeking plume parameters (Plan D)
HOST_SEEKING_SCALE_M    = 100.0f;   // Giraldo 2023, Spitzen 2013, Okumu 2013
HOST_SEEKING_RADIUS_M   = 300.0f;   // Yang 2009 (94% reduction <300m)
HOST_SEEKING_STARVATION_DAYS = 7;   // start 7, tune down to 5 if D1 high

// Oviposition-seeking plume parameters (Plan D)
OVIPOSITION_SCALE_M     = 50.0f;    // Okal 2013 water-vapour plume decay
OVIPOSITION_RADIUS_M    = 500.0f;   // Okal 2013, Lindh 2015 (9+ m scaled up)
```

**File**: `mal-core/src/mal_core/abm/src/host_seeking.cpp`

- Line 35: change `constexpr float kScale = 35.0f;` to `constexpr float kScale = HOST_SEEKING_SCALE_M;` (or read via global in `compute_attraction`).
- In `compute_attraction` (line 85), replace the magic `35.0f` literal with `HOST_SEEKING_SCALE_M`.

**File**: `mal-core/src/mal_core/abm/include/mal_abm_fast/host_seeking.hpp`

- Line 73: change `search_radius_m = 70.0f` default to `search_radius_m = 300.0f`.

**File**: `mal-core/src/mal_core/abm/tests/calibration/scorers/D13_host_seeking_distance.py`

- Update constants:
  ```python
  EXPECTED_SCALE_M = 100.0
  MIN_SCALE_M = 70.0
  MAX_SCALE_M = 300.0
  ```
- Update docstring: anchor Yang 2009 (300m = 94% reduction) as MAX; Giraldo 2023 (60m), Spitzen 2013 (60–70m), Okumu 2013 (70m significant) for MIN.

**File**: `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` (D13 section lines 78–82)

```yaml
D13_host_seeking_distance:
  min_score: 0.60
  max_delta: -0.25
  hard_floor: 0.30
  source: "Yang 2009: 300m = 94% malaria reduction; Giraldo 2023: 60m CO2 plume; Okumu 2013: 70m significant attraction"
```

### Phase 2 — Wire directed host-seeking flight (Plan B core)

**File**: `mal-core/src/mal_core/abm/include/mal_abm_fast/host_seeking.hpp`

Add to the class:

```cpp
std::optional<Coord> detect_host_cell(int row, int col,
                                     double range_m = 2000.0) const;
```

Implementation (new method): scan all `HostCell` records, filter by `compute_attraction > 0.5` and Euclidean distance ≤ `range_m`, return argmax by attraction. O(N) per call; mitigate with `std::unordered_map<tuple<row,col,day>, std::optional<Coord>>` cache (expire every 5 days).

**File**: `mal-core/src/mal_core/abm/include/mal_abm_fast/gonotrophic_cycle.hpp` (lines 25-37)

`HOST_APPROACH` is already declared — confirm it remains in the enum and add a sibling:

```cpp
OVIPOSITION_APPROACH,  // NEW (Phase 3)
```

**File**: `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` (gonotrophic loop, lines 434-519)

Add before the existing `case HOST_SEEKING:`:

```cpp
case GonotrophicState::HOST_APPROACH: {
    auto target = host_seeking_model_->detect_host_cell(
        soa_.cell_row[idx], soa_.cell_col[idx], /*range_m=*/2000.0);
    if (!target) {
        soa_.state[idx] = GonotrophicState::HOST_SEEKING;  // back to random walk
        break;
    }
    auto step = host_seeking_model_->approach_vector(
        soa_.cell_row[idx], soa_.cell_col[idx],
        target->row, target->col, aoi_, /*step_size_m=*/50.0f);
    soa_.cell_row[idx] = step.row;
    soa_.cell_col[idx] = step.col;
    update_patch_id(idx, step.row, step.col);  // Phase 4 hook
    if (step.row == target->row && step.col == target->col) {
        soa_.state[idx] = GonotrophicState::HOST_SEEKING;  // arrived; resume normal host-seeking
        soa_.fed_today[idx] = 1;
    }
    soa_.days_in_state[idx] += 1;
    if (soa_.days_in_state[idx] >= HOST_SEEKING_STARVATION_DAYS) {
        soa_.alive[idx] = 0;
        soa_.cause_of_death[idx] = CauseOfDeath::Starvation;
    }
    break;
}
```

In the existing `case HOST_SEEKING:`, add a starvation timer branch:
```cpp
soa_.days_in_state[idx] += 1;
if (soa_.days_in_state[idx] >= HOST_SEEKING_STARVATION_DAYS) {
    soa_.alive[idx] = 0;
    soa_.cause_of_death[idx] = CauseOfDeath::Starvation;
}
```

**File**: `mal-core/src/mal_core/abm/tests/host_seeking_tests.cpp` (new)

```cpp
#include <gtest/gtest.h>
#include "mal_abm_fast/host_seeking.hpp"

TEST(HostSeeking, ApproachVectorTowardTarget) {
    HostSeekingModel m;
    auto step = m.approach_vector(0, 0, /*target_row=*/3, /*target_col=*/4,
                                   AOI{} /* minimal */, 50.0f);
    EXPECT_TRUE(step.row >= 0 && step.row <= 3);
    EXPECT_TRUE(step.col >= 0 && step.col <= 4);
}

TEST(HostSeeking, ScaleConstantIsBiological) {
    HostSeekingModel m;
    // Sanity: the kernel's effective range should accommodate Yang 2009's 300m.
    // At distance=300, attraction should still be > 0.05 (5% of max).
    float attraction = m.cell_attraction_for_test(/*dist_m=*/300.0f);
    EXPECT_GT(attraction, 0.05f);
}
```

### Phase 3 — Oviposition-seeking kernel (NEW class)

**File**: `mal-core/src/mal_core/abm/include/mal_abm_fast/oviposition_seeking.hpp` (new)

Mirror `host_seeking.hpp` structure:

```cpp
#pragma once
#include "aoi.hpp"
#include "habitat_engine.hpp"
#include <optional>
#include <vector>

struct BreedingAttraction {
    float distance_m = 0.0f;
    float attraction = 0.0f;
    int32_t patch_id = -1;
};

class OvipositionSeekingModel {
public:
    explicit OvipositionSeekingModel(double scale_m = 50.0, double radius_m = 500.0);
    
    // Compute water-vapour + VOC attraction at each cell within radius.
    std::vector<BreedingAttraction> compute_attraction(
        int row, int col, const HabitatEngine& hab,
        const AOI& aoi, double search_radius_m = -1.0) const;
    
    // Select best breeding site by attraction (argmax, no roulette — sites are not "competing" for the same egg batch).
    std::optional<HabitatPatch> select_site(
        const std::vector<BreedingAttraction>& attractions) const;
    
    // Detect any viable breeding site within range.
    std::optional<std::pair<int, int>> detect_breeding_cell(
        int row, int col, const HabitatEngine& hab,
        const AOI& aoi, double range_m = 2000.0) const;
    
    // Directed step toward selected breeding site.
    struct Coord step_toward(int from_row, int from_col,
                             int target_row, int target_col,
                             const AOI& aoi, double step_size_m = 50.0) const;

private:
    double scale_m_;
    double radius_m_;
};
```

**File**: `mal-core/src/mal_core/abm/src/oviposition_seeking.cpp` (new)

- `compute_attraction`: for each activated patch within `search_radius_m`, compute `attraction = patch.twi_value × patch.water_frac × exp(-dist_m / 50)` (water-vapour plume decay). Sort descending.
- `select_site`: argmax (not roulette — oviposition is a single event, not a host-choice).
- `detect_breeding_cell`: scan, filter by `attraction > 0.3`, return argmax by `twi_value × water_frac`.
- `step_toward`: same pattern as `HostSeekingModel::approach_vector` — move up to `step_size_m` toward target.

**File**: `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_engine.hpp` (existing)

Add:
```cpp
bool is_viable_oviposition_site(int row, int col) const;
// Returns true iff cell (row, col) has:
//   - any HabitatPatch with hab_pluvial_pool=true AND patch_states[t].activated==true
//   - OR dynamic cell satisfying (twi > 8 ∧ water_frac > 0 ∧ rain > 15mm) at evaluation time
```

**File**: `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` (lines 448-482, OVIPOSITION_SEEKING block)

Replace the binary site check with:

```cpp
case GonotrophicState::OVIPOSITION_SEEKING: {
    auto target = oviposition_seeking_model_->detect_breeding_cell(
        soa_.cell_row[idx], soa_.cell_col[idx],
        *habitat_engine_, aoi_, /*range_m=*/2000.0);
    if (!target) {
        // No breeding site within 2km; back to OVIPOSITION_SEEKING with random walk
        // (existing behaviour; today+1, female tries again).
        soa_.days_in_state[idx] += 1;
        break;
    }
    auto step = oviposition_seeking_model_->step_toward(
        soa_.cell_row[idx], soa_.cell_col[idx],
        target->first, target->second, aoi_, 50.0f);
    soa_.cell_row[idx] = step.row;
    soa_.cell_col[idx] = step.col;
    update_patch_id(idx, step.row, step.col);  // Phase 4 hook
    if (habitat_engine_->is_viable_oviposition_site(step.row, step.col)) {
        // Arrived at a viable site
        g_state = GonotrophicState::OVIPOSITING;
        soa_.fed_today[idx] = 0;  // not a host feed
    }
    soa_.days_in_state[idx] += 1;
    if (soa_.days_in_state[idx] >= OVIPOSITION_SEEKING_TIMEOUT_DAYS) {
        // Skip-oviposition: female retains eggs, goes back to HOST_SEEKING
        // (matches literature: females skip poor sites and try again)
        soa_.state[idx] = GonotrophicState::HOST_SEEKING;
        soa_.days_in_state[idx] = 0;
    }
    break;
}
```

Add `OVIPOSITION_SEEKING_TIMEOUT_DAYS = 7` to `wire.hpp` (literature: females skip unsuitable sites and re-enter host-seeking to obtain another blood meal; Lindh 2014, Mwingira 2020).

Add `OVIPOSITION_APPROACH` state to gonotrophic cycle if a separate "actively approaching" substate is preferred; otherwise use the same `OVIPOSITION_SEEKING` state with the directed-walk logic embedded.

**File**: `mal-core/src/mal_core/abm/tests/oviposition_seeking_tests.cpp` (new)

```cpp
TEST(OvipositionSeeking, AttractionDecaysWithDistance) {
    OvipositionSeekingModel m(50.0, 500.0);
    auto a = m.compute_attraction(/*row=*/0, /*col=*/0, /*hub=*/stub, /*aoi=*/stub, 500.0);
    // Expect: cells closer to (0,0) have higher attraction than distant cells
}

TEST(OvipositionSeeking, DetectBreedingCellFindsWater) {
    // Stub habitat engine with one viable patch at (3, 4) and one dry patch at (10, 10)
    // Expect: detect_breeding_cell(0, 0, ...) returns (3, 4)
}
```

### Phase 4 — Patch tracking fix (structural bug)

**File**: `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp`

Add helper (somewhere near top of class definition):

```cpp
void MosquitoSubmodel::update_patch_id(int idx, int new_row, int new_col) {
    // Snap to nearest activated patch within 500m of new position.
    // Fallback: leave patch_id unchanged (skip oviposition semantics).
    int32_t best_patch = -1;
    double best_dist_m = std::numeric_limits<double>::infinity();
    for (const auto& ps : patch_states_) {
        if (!ps.activated) continue;
        double d = std::hypot(ps.row - new_row, ps.col - new_col) * aoi_.resolution_m;
        if (d > 500.0) continue;
        if (d < best_dist_m) {
            best_dist_m = d;
            best_patch = ps.patch_id;
        }
    }
    if (best_patch >= 0) {
        soa_.patch_id[idx] = best_patch;
    }
    // else: leave patch_id unchanged — female continues searching
}
```

Apply this helper at every position-change site:
- `mosquito_submodel.cpp`: after HOST_APPROACH arrival (Phase 2 hook).
- `mosquito_submodel.cpp:OVIPOSITION_SEEKING` (Phase 3 hook).
- `mosquito_submodel.cpp:659-662`: after windborne landing and state reset.
- `mosquito_submodel.cpp:673-686`: after local Gaussian dispersal cell snap.
- `mosquito_submodel.cpp:469-482`: in OVIPOSITING branch **before** `cohort_bank_.add_eggs(soa_.patch_id[si], N)`.

**File**: `mal-core/src/mal_core/abm/tests/patch_tracking_tests.cpp` (new)

```cpp
TEST(PatchTracking, EggsLandAtDestinationNotNatal) {
    // Construct mosquito at natal cell (0, 0) with patch_id=P1.
    // Apply windborne dispersal that lands at (5, 5) where patch P2 is activated.
    // Advance to OVIPOSITION_SEEKING → OVIPOSITING.
    // Expect: cohort_bank_ has eggs in P2, not P1.
}
```

### Phase 5 — New scorers

| ID | File | Weight | Target | Source |
|---|---|---|---|---|
| **D16** `spread_rate` | `D16_spread_rate.py` (new) | 0.15 | p90 displacement in **[5, 20] km** at day 180 | Thomas 2013 |
| **D17** `host_clustering` | `D17_host_clustering.py` (new) | 0.10 | Variance of adult density per host-cell cluster in upper tertile ≥ 0.6 | Depinay 2004; North & Godfray 2018 |
| **D18** `oviposition_fidelity` | `D18_oviposition_fidelity.py` (new, optional) | 0.10 | Eggs laid per patch (top tertile) / uniform baseline ≥ 1.5 | Lindh 2015 (gravid site preference); Mwingira 2020 |

**D13** is updated (not added). **D1** is reused unchanged.

**File**: `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py`

Add to `DEFAULT_WEIGHTS`:
```python
"D16_spread_rate": 0.15,
"D17_host_clustering": 0.10,
"D18_oviposition_fidelity": 0.10,
```

D18 is optional — register only if the oviposition-kernel signature is measurable on a 30-day fast run. If not measurable at fast tier, defer to full tier.

### Phase 6 — Drift fixes

| File | Line | Current | Authoritative | Reason |
|---|---|---|---|---|
| `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` | 53 | `ADULT_DISPERSE_PROB = 0.05f` | **keep 0.05** | Reconcile with `dispersal-kernel-calibration.md` §5 which says 0.10 in narrative; code is authoritative per wire.hpp header comment. |
| `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` | 54 | `ADULT_DISPERSE_SIGMA_M = 450.0f` | **keep 450** | Costantini 1996 midpoint; doc spec at `docs/specs/abm/wire-spec.md:151` says 1000 — update spec to 450. |
| `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` | 55 | `ADULT_DISPERSE_MAX_M = 2000.0f` | **keep 2000** | Matches Plan B detect_host_cell range. |
| `mal-ghana-sim/src/mal_ghana_sim/abm/mosquito_submodel.py` | 82 | `ADULT_DISPERSE_SIGMA_M: float = 1000.0` | **update to 450.0** | Stale drift; matches authoritative C++ value. |
| `docs/specs/abm/wire-spec.md` | 151 | `ADULT_DISPERSE_SIGMA_M = 1000.0` | **update to 450.0** | Stale drift; matches Costantini 1996 anchor. |

The drift fixes are doc-sync only — no behaviour change to existing dispersal constants. Dispersal is **not** the bug Plan D is fixing (the bug is `patch_id` + kernel range + directed flight), so we leave dispersal constants at the C++ authoritative values.

### Phase 7 — Defer / archive

- **Plan C (`plan-C-oviposition-seeking.md`)**: mark as `superseded-by: plan-D` and move to `docs/plans/completed/dispersal-plans/plan-C-oviposition-seeking.md` after Plan D merges. Rationale: Diallo 2026 explicitly rejects site fidelity; Plan D's `update_patch_id` achieves correctness without inventing a return mechanism.

- **Plan A (`plan-A-windborne.md`)**: no change. Windborne parameters (prob=0.05, survival=0.85, flight_hours=4) are unchanged. Plan D's patch-tracking fix removes the egg-misallocation artefact that Plan A's parameter tuning was partially compensating for.

- **Plan B (`plan-B-host-seeking.md`)**: superseded by Plan D's Phases 1–2 + 4. F1.e parity removal (Section 5) is still a prerequisite.

---

## 5. Pre-requisites

### 5.1 F1.e parity removal (must run first; ~0.3 sessions)

Same as Plan B §5. Plan D cannot ship with `test_abm_fast_parity.py` still in the tree — the `HOST_APPROACH` wiring will trigger parity failures that are unrelated to the kernel change.

| File | Lines | Action |
|---|---|---|
| `mal-core/src/mal_core/abm/README.md` | 19-22, 137-139 | Update F1.e language |
| `../../in-process/perf-cpp-abm-plan.md` | 14, 68, 89, 152, 201, 266, 289, 431, 446-448, 499, 501 | Update F1.e language |
| `mal-core/src/mal_core/abm/tests/test_abm_fast_parity.py` | whole | Delete |
| `mal-ghana-sim/tests/test_abm_fast_parity.py` | whole | Delete |

### 5.2 Recall-before-write

Per AGENTS.md: query the knowledge graph for prior work on:
- Host-seeking / kernel parameters (`Component` + `Pitfall` nodes)
- Oviposition / patch_id bugs (`Pitfall` nodes)
- Dispersal calibration (`Investigation` nodes)

If a relevant node already exists, MERGE into it (don't duplicate). Use `memory_query` before any `memory_node` write.

---

## 6. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **OVIPOSITION kernel performance**: O(N) per gravid female per day. Performance regression in large AOIs. | Med | Med | `std::unordered_map<tuple<row,col,day>, std::optional<...>>` cache; expire every 5 days. Same as Plan B's `detect_host_cell` cache. |
| 2 | **Starvation cascade**: 7-day timer on `HOST_SEEKING` and `HOST_APPROACH` could collapse adult population if D1 is sensitive. | Med | High | Start at 7 days. Decrement only if D1 (expansion) is ≥ 0.75 baseline. Add `OVIPOSITION_SEEKING_TIMEOUT_DAYS = 7` to skip-oviposit instead of die. |
| 3 | **`patch_id` update races with `cohort_bank_` writes**: if `update_patch_id` is called after `add_eggs`, eggs land in wrong patch. | Low | High | Call `update_patch_id` immediately before every `cohort_bank_.add_eggs`. Add `patch_tracking_tests.cpp` regression test. |
| 4 | **D13 regresses during transition**: the scorer validates against the new range [70-300] which spans 230m of biological range; ABM may take 2-3 days of tuning to land inside the pass band. | Med | Low | `max_delta: -0.25` in `thresholds.yaml` permits 0.25 absolute score regression during the run. Phase 1 ships with `kScale=100, radius=300` exact match (score = 1.0) — no regression expected. |
| 5 | **Double-counting with windborne**: if a female is in `HOST_APPROACH` and the daily windborne loop fires, both move the same female the same day. | Low | Low | Windborne applies only to `GRAVID` / `OVIPOSITION_SEEKING` (per `mosquito_submodel.cpp:606-693`). `HOST_APPROACH` is separate. No double-count. |
| 6 | **OVIPOSITION_APPROACH might miss rare, distant breeding sites**: a gravid female that dispersed 2km away from any water in ≤3 days (rare) will time out and skip-oviposit. | Low | Low | Matches Lindh 2014, Mwingira 2020 literature: females do retain eggs and re-enter host-seeking. Population-level reproductive output preserved. |
| 7 | **`update_patch_id` on every dispersal step is expensive**: O(N_patches) per female per day. | Med | Med | Constrain `update_patch_id` to `OVIPOSITION_SEEKING` entry and `OVIPOSITING`. Skip on intermediate dispersal steps (patch_id stays current until the next OVIPOSITION cycle). |
| 8 | **New kernel changes spatial signature**: existing snapshots / regression tests with hard-coded cell positions will break. | Med | Low | Re-record 2-3 regression snapshots after Phases 1+2 ship; archive old snapshots in `tests/snapshots/legacy-pre-plan-d/`. |
| 9 | **`HOST_APPROACH` and `OVIPOSITION_APPROACH` may be entered simultaneously**: a female can't be both host-seeking and ovipositing. | None | None | State machine is single-state. No conflict. |

---

## 7. Files modified

### New files (4)

- `mal-core/src/mal_core/abm/include/mal_abm_fast/oviposition_seeking.hpp`
- `mal-core/src/mal_core/abm/src/oviposition_seeking.cpp`
- `mal-core/src/mal_core/abm/tests/host_seeking_tests.cpp`
- `mal-core/src/mal_core/abm/tests/oviposition_seeking_tests.cpp`
- `mal-core/src/mal_core/abm/tests/patch_tracking_tests.cpp`
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D16_spread_rate.py`
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D17_host_clustering.py`
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D18_oviposition_fidelity.py` (optional)

### Modified files (~13)

- `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` (new constants + drift note)
- `mal-core/src/mal_core/abm/include/mal_abm_fast/host_seeking.hpp` (`detect_host_cell` declaration, `search_radius_m` default)
- `mal-core/src/mal_core/abm/src/host_seeking.cpp` (kScale → wire.hpp constant)
- `mal-core/src/mal_core/abm/include/mal_abm_fast/gonotrophic_cycle.hpp` (add `OVIPOSITION_APPROACH` if used)
- `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` (HOST_APPROACH wiring, OVIPOSITION_SEEKING replacement, update_patch_id helper, starvation timers, OVIPOSITION timeout)
- `mal-core/src/mal_core/abm/include/mal_abm_fast/habitat_engine.hpp` (`is_viable_oviposition_site` declaration)
- `mal-core/src/mal_core/abm/src/habitat_engine.cpp` (`is_viable_oviposition_site` implementation)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D13_host_seeking_distance.py` (constants update)
- `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` (D13 source citation)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py` (D16, D17, D18 weights)
- `mal-ghana-sim/src/mal_ghana_sim/abm/mosquito_submodel.py` (drift fix: 1000 → 450)
- `docs/specs/abm/wire-spec.md` (drift fix: 1000 → 450)
- `docs/plans/in-process/dispersal-plans/plan-B-host-seeking.md` (mark superseded)
- `docs/plans/in-process/dispersal-plans/plan-C-oviposition-seeking.md` (mark superseded)

### Deleted files (F1.e prerequisite)

- `mal-core/src/mal_core/abm/tests/test_abm_fast_parity.py`
- `mal-ghana-sim/tests/test_abm_fast_parity.py`

---

## 8. Effort estimate

| Phase | Sessions |
|---|---|
| 5.1 F1.e removal (prerequisite) | 0.3 |
| 1. Kernel expansion (constants + D13 update) | 0.5 |
| 2. Wire directed host-seeking flight (HOST_APPROACH) | 1.0 |
| 3. Oviposition-seeking kernel (new class + integration) | 1.5 |
| 4. Patch tracking fix (`update_patch_id`) | 0.5 |
| 5. New scorers (D16, D17, D18) + composite weights | 0.6 |
| 6. Drift fixes (Python + spec sync) | 0.3 |
| Tuning & regression (fast suite, 30/180-day sims) | 0.5 |
| **Total** | **~5.2** |

---

## 9. Acceptance criteria

### Functional

- [ ] `pytest -m fast -v` passes
- [ ] D1 (expansion) ≥ 0.70
- [ ] D13 (host-seeking distance, new range) ≥ 0.75
- [ ] D16 (spread_rate) ≥ 0.70
- [ ] D17 (host_clustering) ≥ 0.60
- [ ] D18 (oviposition_fidelity, if registered) ≥ 0.60
- [ ] Composite score ≥ 0.70
- [ ] No scorer regresses > 0.05 vs the pre-Plan-D baseline

### 180-day Ghana sim

- [ ] `spread_p90_km` ∈ **[5, 20]**
- [ ] `host_cell_cluster_variance_top_tertile` ≥ 0.6
- [ ] `eggs_per_patch_top_tertile_ratio` ≥ 1.5 (D18 metric)
- [ ] No patch receives > 30% of all eggs (sanity check against the `patch_id` bug)

### Unit tests

- [ ] `HostSeeking.ApproachVectorTowardTarget` passes
- [ ] `HostSeeking.ScaleConstantIsBiological` passes (300m cell has attraction > 0.05)
- [ ] `OvipositionSeeking.AttractionDecaysWithDistance` passes
- [ ] `OvipositionSeeking.DetectBreedingCellFindsWater` passes
- [ ] `PatchTracking.EggsLandAtDestinationNotNatal` passes
- [ ] All existing C++ tests continue to pass
- [ ] No new compiler warnings (`-Wall -Wextra`)

### Performance

- [ ] Fast-tier 30-day sim completes in < 60s (regression check)
- [ ] No per-day O(N²) loops introduced

### Knowledge graph

- [ ] Memory node(s) created for: Plan D implementation, oviposition kernel architecture, patch_id fix.
- [ ] Pitfall node for the original `patch_id` bug (closed status, with link to fix commit).
- [ ] Pattern node for "sensing-without-direction" defect (closed status, with link to fix commit).

---

## 10. Comparison to other plans (cross-link)

| Axis | Plan A | Plan B (superseded) | Plan C (superseded) | Plan D (this) |
|---|---|---|---|---|
| Mechanism | Wind (passive) | Host-seeking (active) | Site fidelity (active) | Host + oviposition (active, parallel kernels) |
| New state | none | `HOST_APPROACH` wired | `natal_patch_id` field | `HOST_APPROACH` + `OVIPOSITION_APPROACH` + `update_patch_id` |
| Spatial signature | Smooth radial front | Clustered around villages | Clustered around natal patch | Clustered around villages AND breeding sites |
| Kernel range fix | No | No (still 35m/70m) | No | **Yes (100m/300m)** |
| Oviposition kernel | Random walk | Random walk | Site fidelity walk | **Directed walk + plume detection** |
| patch_id bug fix | No | No | Side-effect | **Yes (explicit)** |
| New scorers | D16 | D16, D17 | D16, D18 | D16, D17, D18 |
| Risk | Low | Med | Med | Med |
| Sessions | 1.5 | 3.0 | 2.0 | 5.2 |
| Literature basis | Windborne literature | Host-seeking literature | Site fidelity (contested) | Host + oviposition + no-site-fidelity |
| Status | merged | superseded | superseded | **proposed** |

Plan D is the **strongest fit** because it:
1. Anchors on literature that is **not contested** (Giraldo 2023, Okumu 2013, Yang 2009, Okal 2013, Lindh 2015).
2. **Rejects** the literature-contested mechanisms (Plan C's site fidelity is rejected by Diallo 2026).
3. Fixes the structural `patch_id` bug that all three dispersal mechanisms inherit.
4. Captures **two distinct biological processes** (host-seeking and oviposition) with parallel, structurally similar kernels.

---

## 11. Knowledge graph integration

After Phase 1 merges, write the following nodes (per `project-memory` skill, `memory_node`):

| Type | Name | Summary |
|---|---|---|
| `Architecture` | `arch-kernel-host-seeking` | Host-seeking kernel: 100m scale, 300m radius, CO₂ + body-odour. Plan D Phase 1. |
| `Architecture` | `arch-kernel-oviposition-seeking` | Oviposition-seeking kernel: 50m scale, 500m radius, water-vapour + VOC. Plan D Phase 3. |
| `Pitfall` | `pitfall-patch-id-stale-after-dispersal` | Eggs land in natal patch, not destination. Closed by Plan D Phase 4. |
| `Pitfall` | `pitfall-host-seeking-range-too-short` | kScale=35m underestimates Yang 2009 300m reach. Closed by Plan D Phase 1. |
| `Pattern` | `pattern-sensing-without-direction` | Implementation computes attraction but never calls approach_vector. Closed for host + oviposition by Plan D. |
| `Investigation` | `inv-oviposition-site-detection-literature` | Literature review: Okal 2013, Lindh 2015, Mwingira 2020, Herrera-Varela 2014. |
| `Investigation` | `inv-no-site-fidelity-diallo-2026` | Diallo 2026 MRR: 70% recaptured in different zone. Plan C invalidated. |
| `Operational` | `op-m7-8-mosquito-search-kernels` | Milestone M7.8: Plan D implementation. |

---

## 12. Open questions for supervisor before implementation

1. **OVIPOSITION_APPROACH as separate state?** Or fold directed walk into `OVIPOSITION_SEEKING`?
   - Recommendation: fold into `OVIPOSITION_SEEKING` (simpler state machine, matches literature that doesn't distinguish "search" from "approach" for oviposition).

2. **D18 (oviposition_fidelity) registered at fast tier?** Or defer to full tier?
   - Recommendation: register at full tier only. Fast-tier 30-day sims have too few oviposition events for stable statistics.

3. **`update_patch_id` cache?** Or recompute every time?
   - Recommendation: recompute only on state transitions (HOST_APPROACH arrival, OVIPOSITION_SEEKING entry, windborne landing). Skip intermediate dispersal snaps. Performance impact negligible.

4. **Backward compatibility for `kScale = 35.0f` callers?** Some tests may hard-code the value.
   - Recommendation: keep `kScale = HOST_SEEKING_SCALE_M` as `constexpr float = 100.0f` in the header. Search-and-update any callers; add a CHANGELOG note.

5. **Should Plan B be marked `superseded-by: plan-D` in its front matter, or kept as historical reference?**
   - Recommendation: mark superseded, keep file accessible. Plan B's F1.e prerequisite (§5.1) and core wiring approach (§3.1-3.6) are absorbed into Plan D — the file documents the design journey.

---

## 13. Sign-off

Implementation cannot begin until:

1. The user (davidflorezmazuera) confirms Phase 1-3 should ship together (recommended), or phases can ship incrementally.
2. F1.e removal prerequisite is approved.
3. Memory nodes for `pitfall-patch-id-stale-after-dispersal` and `pitfall-host-seeking-range-too-short` are written **before** code changes (per `recall-before-write`).

Estimated wall-clock to merge: **5–7 sessions** (single-developer, sequential phases). Subagent parallelisation possible for Phases 5+6 (scorers + drift) once Phases 1–4 are stable.
