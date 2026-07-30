# Plan B — Host-Seeking Directed Flight

| Field | Value |
|---|---|
| **Plan ID** | B |
| **Status** | proposed |
| **Hypothesis** | A *Anopheles* female in the `HOST_SEEKING` state performs **active, directed upwind flight** toward a detected host plume; replacing the current isotropic random walk with a one-cell-per-day step along the existing (but currently unused) `HostSeekingModel::approach_vector` is the dominant spatial-spread mechanism the current ABM is missing. |
| **Risk class** | Medium — touches the state machine, two existing dead-code paths, and adds a starvation timer. |
| **Effort** | ~3 sessions |
| **Owner (TBD)** | `wt/plan-b-host-seeking` → branch `common/abm-plan-b` |

---

## 1. Biological hypothesis

In the field, host-seeking *Anopheles* females do **not** disperse isotropically. They engage in **appetitive upwind flight** along a CO₂ / odour plume (the well-studied "optomotor anemotaxis" — see Depinay 2004 and the existing `HostSeekingModel::approach_vector` docstring). Once a host is detected at long range, the female turns and walks (in grid-cell terms) toward that host cell. After 5+ days of unsuccessful search, she dies of starvation.

The current ABM has the **sensing** (it computes `compute_attraction` at line 85 of `host_seeking.cpp`) but discards the **direction** — the `approach_vector` function is implemented at line 171 but is never called from `advance_day`'s gonotrophic loop (lines 434–519). The result: host-seeking females diffuse randomly, which under-estimates the rate at which populations colonise new villages.

We hypothesise that **wiring `approach_vector` into `HOST_SEEKING` as a directed one-cell-per-day step**, plus adding a starvation timer, will produce a clustered spatial signature (villages get *more* mosquitoes than the windborne-only model predicts) without inflating the long tail.

## 2. Literature basis

| Source | File | Key numbers used |
|---|---|---|
| **Depinay et al. 2004** | `papers/anopheles-dynamics/depinay-2004-anopheles-simulation-model.md` | Active host-seeking flight along plumes; supports directed (non-random) walk during `HOST_SEEKING`. |
| **Costantini 1996** | `papers/anopheles-dynamics/costantini-1996-anopheles-density-survival-dispersal.md` | 350–650 m/day outward displacement is a *net* of directed + passive; supports adding a 200–400 m/d directed component. |
| **Thomas 2013** | `papers/anopheles-dynamics/thomas-2013-anopheles-gambiae-gambia-dispersal.md` | p90 1.28 km / p95 1.67 km — these are the targets for D16. Plan B's host-directed step (200–400 m/d) plus Plan A's windborne tail is expected to reach this. |
| **Huestis 2019** | `../m7-6-wind-dispersal-plan.md` | 6–11 h flights — supports the daily-step, multi-hour, directed movement. |
| **North & Godfray 2018** | (cited in `dispersal-kernel-calibration.md`) | Settlement-to-settlement dispersal d=0.01; the *variance* of adult density per settlement cluster (D17) should match this. |

## 3. Code changes

### 3.1 Wire `HOST_APPROACH` state (`gonotrophic_cycle.hpp` lines 25–37)

`HOST_APPROACH` is declared in the state enum but unused. Plan B uses it as the **active-approach** substate of `HOST_SEEKING`:

```
HOST_SEEKING ──(host detected at > 2 km)──▶ HOST_APPROACH
HOST_APPROACH ──(host cell reached)──▶ FEEDING
HOST_SEEKING ──(5 days no feed)──▶ starvation death
HOST_APPROACH ──(5 days no feed)──▶ starvation death
```

### 3.2 `mosquito_submodel.cpp::advance_day` gonotrophic loop (lines 434–519)

Add a new switch branch before the existing `case HOST_SEEKING:`:

```cpp
// inside the gonotrophic state machine, after the existing case HOST_SEEKING:
case GonotrophicState::HOST_APPROACH: {
    auto target = host_seeking_model.detect_host_cell(soa.cell_row[idx], soa.cell_col[idx], /*range_m=*/2000);
    if (!target) {
        soa.state[idx] = GonotrophicState::HOST_SEEKING;  // back to random walk
        break;
    }
    auto step = host_seeking_model.approach_vector(soa.cell_row[idx], soa.cell_col[idx], *target);
    soa.cell_row[idx] = step.row;
    soa.cell_col[idx] = step.col;
    if (step.row == target->row && step.col == target->col) {
        soa.state[idx] = GonotrophicState::FEEDING;
        soa.fed_today[idx] = 1;
    }
    soa.days_in_state[idx] += 1;
    if (soa.days_in_state[idx] >= 5) {
        soa.alive[idx] = 0;
        soa.cause_of_death[idx] = CauseOfDeath::Starvation;
    }
    break;
}
```

### 3.3 Add `HOST_SEEKING` starvation timer (5 days)

Same pattern as 3.2 inside the existing `case HOST_SEEKING:` — track `soa.days_in_state[idx]`, kill on day 5.

### 3.4 OVIPOSITION_SEEKING directed walk

Reuse the same pattern: at `OVIPOSITION_SEEKING` entry, find the **nearest viable patch** within 2 km (using the new `HabitatEngine::nearest_viable_cell` from Plan A), then walk one cell per day toward it. On arrival, deposit eggs (existing `oviposition deposit` lines 469–482, unchanged). Add the same 5-day starvation timer.

### 3.5 `host_seeking.cpp::approach_vector` (line 171) — already implemented

No change. This is the whole point of Plan B: the function is *correct*, just never called. Add a unit test:

```cpp
// host_seeking_tests.cpp  (new)
TEST(HostSeeking, ApproachVectorTowardTarget) {
    HostSeekingModel m;
    auto step = m.approach_vector(0, 0, Coord{3, 4});  // expect (1, 1) or (0, 1) or (1, 0)
    EXPECT_TRUE(step.row == 1 || step.col == 1);
}
```

### 3.6 `host_seeking.cpp::compute_attraction` (line 85) — already correct

No change. Used to decide when to transition `HOST_SEEKING → HOST_APPROACH`.

### 3.7 `host_seeking.cpp::detect_host_cell` — new

```cpp
// host_seeking.hpp
std::optional<Coord> detect_host_cell(int row, int col, double range_m = 2000.0) const;
// Returns the highest-attraction host cell within range_m, or nullopt.
```

Implementation: scan all `HostCell` records (already in `HostSeekingModel`), filter by `compute_attraction > 0.5` and Euclidean distance ≤ range_m, return argmax.

## 4. Scorer(s) — new

| ID | File | Weight | Target | Source |
|---|---|---|---|---|
| **D16** `spread_rate` | `.../D16_spread_rate.py` | 0.15 | p90 displacement in **[5, 20] km** at day 180 | Thomas 2013 |
| **D17** `host_clustering` | `.../D17_host_clustering.py` | 0.10 | Variance of adult density per host-cell cluster in upper tertile (villages are clearly preferred over the matrix) | Depinay 2004; North & Godfray 2018 |

D13 (`D13_host_seeking_distance.py`) is **reused** — it already measures the mean distance between adult females and the nearest host cell at day 30. Plan B should drive D13 above 0.75 (target 0.5–1.5 km median distance).

D1 reused.

## 5. F1.e parity removal — required file touches

(Same as Plan A. The implementing agent must do F1.e first.)

| File | Lines | Action |
|---|---|---|
| `mal-core/src/mal_core/abm/README.md` | 19–22, 137–139 | Update F1.e language |
| `../../in-process/perf-cpp-abm-plan.md` | 14, 68, 89, 152, 201, 266, 289, 431, 446–448, 499, 501 | Update F1.e language |
| `mal-core/src/mal_core/abm/tests/test_abm_fast_parity.py` | whole | Delete |
| `mal-ghana-sim/tests/test_abm_fast_parity.py` | whole | Delete |

## 6. Risks

1. **Starvation cascades**: a too-aggressive 5-day starvation timer will collapse the adult population, breaking D1 (expansion) and D13. Mitigation: start with 7 days, decrement only if D1 is still high.
2. **`detect_host_cell` is O(N) over all HostCells**: per-female per-day. Performance regression in large AOIs. Mitigation: cache by (row, col, day) in a `std::unordered_map`; expire every 5 days.
3. **State machine interaction with F1.e parity suite**: `HOST_APPROACH` was untested. Adding a transition without deleting the parity test will cause 5+ parity failures that the implementer may misdiagnose. **Do the F1.e removal first.**
4. **Determinism**: the new directed walk changes the spatial pattern; if any test relied on a specific seed producing a specific cell, it will break. Mitigation: re-record 2–3 regression snapshots and rebase.
5. **Double-counting with Plan A's windborne**: in the orchestrator integration, Plan B's directed walk may *also* trigger a windborne move (if `ADULT_DISPERSE_PROB` fires the same day). Plan B keeps `ADULT_DISPERSE_PROB = 0.15` unchanged — the *windborne* boost from Plan A is a separate channel.

## 7. Files modified

- `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` (gonotrophic loop, lines 434–519)
- `mal-core/src/mal_core/abm/src/host_seeking.hpp` (new `detect_host_cell`)
- `mal-core/src/mal_core/abm/src/host_seeking.cpp` (no change to `approach_vector` line 171; `compute_attraction` line 85 unchanged)
- `mal-core/src/mal_core/abm/src/gonotrophic_cycle.hpp` (HOST_APPROACH state now live)
- `mal-core/src/mal_core/abm/src/wire.hpp` (no changes; Plan A constants may or may not be applied — see orchestrator §4)
- `mal-core/src/mal_core/abm/src/habitat_engine.hpp` (Plan A helper reused)
- `mal-core/src/mal_core/abm/tests/host_seeking_tests.cpp` (new)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D16_spread_rate.py` (new)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D17_host_clustering.py` (new)
- `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` (D16, D17)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py` (weights)
- `mal-core/src/mal_core/abm/README.md` (F1.e)
- `../../in-process/perf-cpp-abm-plan.md` (F1.e)
- `mal-core/src/mal_core/abm/tests/test_abm_fast_parity.py` (delete)
- `mal-ghana-sim/tests/test_abm_fast_parity.py` (delete)

## 8. Effort estimate

| Phase | Sessions |
|---|---|
| F1.e removal (safe-first) | 0.3 |
| D16 + D17 scorers + thresholds | 0.6 |
| Wire HOST_APPROACH + starvation timer | 1.0 |
| OVIPOSITION_SEEKING directed walk | 0.4 |
| `detect_host_cell` + cache + unit test | 0.4 |
| Run fast suite, tune starvation, run 30/180-day sims | 0.3 |
| **Total** | **~3.0** |

## 9. Acceptance criteria

- [ ] `pytest -m fast -v` passes; D1 ≥ 0.70, D13 ≥ 0.75, D16 ≥ 0.70, D17 ≥ 0.60, no scorer regresses > 0.05 vs baseline.
- [ ] Day-180 Ghana sim: `spread_p90_km` ∈ **[5, 20]**, `host_cell_cluster_variance_top_tertile` ≥ 0.6.
- [ ] Unit test `HostSeeking.ApproachVectorTowardTarget` passes.
- [ ] CMake C++ tests pass; no new compiler warnings.
- [ ] Composite score ≥ 0.70.
- [ ] `gitagent propose --agent plan-b` succeeds with confidence ≥ 0.80.

## 10. Comparison to other plans (cross-link)

| Axis | Plan A | Plan B (this) | Plan C |
|---|---|---|---|
| Mechanism | Wind (passive) | Host-seeking (active) | Oviposition-site (active) |
| New state | none | `HOST_APPROACH` wired | `natal_patch_id` |
| Spatial signature | Smooth radial front | Clustered around villages | Clustered around natal + ovip patches |
| New scorers | D16 | D16, D17 | D16, D18 |
| Risk | Low | Med | Med |
| Sessions | 1.5 | 3 | 2 |

Plan B is the **strongest fit** if the spatial signature in the empirical data shows strong village-clustering (which the Ghana DHS cluster data does — see `mal-data-explorer/` village density maps).
