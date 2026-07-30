# Plan C — Oviposition-Site-Seeking + Site Fidelity

| Field | Value |
|---|---|
| **Plan ID** | C |
| **Status** | proposed |
| **Hypothesis** | Gravid *Anopheles* females exhibit strong **site fidelity** to their natal oviposition patch and will return to it (or a nearby viable patch) for oviposition, rather than ovipositing at whatever cell they happen to occupy. Encoding this as a per-mosquito `natal_patch_id` field plus a probabilistic return walk is the dominant realistic mechanism for the *clustered, patch-bound* spatial signature observed in the field. |
| **Risk class** | Medium — adds a new SoA field, changes where eggs are deposited, requires a new walk kernel. |
| **Effort** | ~2 sessions |
| **Owner (TBD)** | `wt/plan-c-oviposition-seeking` → branch `common/abm-plan-c` |

---

## 1. Biological hypothesis

*Anopheles* females emerge from a specific aquatic habitat patch and, after their first gonotrophic cycle, return to **the same patch or a nearby viable patch** to oviposit. This is the *natal patch fidelity* described by Depinay 2004 and quantified in North & Godfray 2018: a returning female has probability ~0.7 of ovipositing at her natal patch if it is still viable, falling back to the nearest viable patch within 2 km otherwise.

The current ABM deposits eggs at `soa.cell_row[idx], soa.cell_col[idx]` (lines 469–482 of `mosquito_submodel.cpp`) — wherever the female happens to be. This produces a **diffuse egg distribution** that does not match the strongly patch-bound pattern observed in field surveys (Yang 2009: removing a single 300 m patch cuts local *Anopheles* density by 94 %).

We hypothesise that adding a per-mosquito `natal_patch_id`, sampling a return-decision at `OVIPOSITION_SEEKING` entry, and walking 200 m steps toward the target will produce a *patch-bound* distribution and a D18 score in the empirically-supported 0.6–0.8 range.

## 2. Literature basis

| Source | File | Key numbers used |
|---|---|---|
| **Depinay et al. 2004** | `papers/anopheles-dynamics/depinay-2004-anopheles-simulation-model.md` | Natal site fidelity in *An. gambiae*; supports the 0.7 return probability. |
| **North & Godfray 2018** | (cited in `dispersal-kernel-calibration.md`) | Settlement-to-settlement d=0.01; supports 2 km radius for fallback. |
| **Yang et al. 2009** | `docs/dispersal-kernel-calibration.md` | 300 m habitat removal → 94 % density reduction; supports the strong patch-bound signature D18 should match. |
| **Costantini 1996** | `papers/anopheles-dynamics/costantini-1996-anopheles-density-survival-dispersal.md` | 350–650 m/day outward displacement — a returning female walking 200 m × 3–4 days is consistent. |
| **Thomas 2013** | `papers/anopheles-dynamics/thomas-2013-anopheles-gambiae-gambia-dispersal.md` | p90 1.28 km — the return walk should not exceed this for a single gonotrophic cycle. |
| **Huestis 2019** | `docs/m7-6-wind-dispersal-plan.md` | 6–11 h flight — 200 m per day (one step) is conservative but consistent with the multi-day return. |

## 3. Code changes

### 3.1 Add `natal_patch_id` to `MosquitoSoA` (`mosquito_state.hpp`)

```cpp
// mosquito_state.hpp  — add to the SoA struct
struct MosquitoSoA {
    // ... existing fields ...
    std::vector<int32_t> natal_patch_id;  // NEW: -1 = unset, else = index into habitat patch list
};
```

`HabitatEngine` must expose a `patch_id_for_cell(row, col) -> int32_t` helper that returns the patch id of the cell, or -1 if the cell is not in any registered patch.

### 3.2 Set `natal_patch_id` at emergence (`mosquito_submodel.cpp::advance_day` lines 396–425)

```cpp
// at adult emergence (existing code that creates new adults)
soa.natal_patch_id[new_idx] = habitat_engine.patch_id_for_cell(
    soa.cell_row[new_idx], soa.cell_col[new_idx]
);
```

### 3.3 Return-decision at `OVIPOSITION_SEEKING` entry

```cpp
// gonotrophic loop, on transition to OVIPOSITION_SEEKING
case GonotrophicState::OVIPOSITION_SEEKING: {
    // ... existing entry logic ...
    double u = uniform_rng(soa.rng[idx]);
    int32_t target_patch;
    if (u < 0.7 && soa.natal_patch_id[idx] >= 0
        && habitat_engine.is_patch_viable(soa.natal_patch_id[idx])) {
        target_patch = soa.natal_patch_id[idx];   // site fidelity
    } else {
        target_patch = habitat_engine.nearest_viable_patch(
            soa.cell_row[idx], soa.cell_col[idx], /*radius_m=*/2000.0
        );
    }
    soa.oviposition_target_patch[idx] = target_patch;  // NEW SoA field
    break;
}
```

Add a new SoA field `oviposition_target_patch` (int32_t) so the walk code in 3.4 knows the target.

### 3.4 Walk in 200 m steps toward target — new helper

`mosquito_submodel.cpp::walk_toward_patch(idx, target_patch)` — a per-day function:

```cpp
// returns true if patch reached this step
bool walk_toward_patch(int idx, int32_t target_patch) {
    auto target_rc = habitat_engine.patch_centroid(target_patch);
    auto cur = std::make_pair(soa.cell_row[idx], soa.cell_col[idx]);
    auto d = gaussian_step_kernel(cur, target_rc, /*sigma_m=*/200.0, soa.rng[idx]);
    // d is a (row, col) offset sampled from a Gaussian with sigma=200m,
    // biased toward target by 0.7 (so 70% of the step is toward the target,
    // 30% is isotropic Gaussian noise).
    soa.cell_row[idx] += d.first;
    soa.cell_col[idx] += d.second;
    return soa.cell_row[idx] == target_rc.first && soa.cell_col[idx] == target_rc.second;
}
```

Add a 5-day starvation timer (same pattern as Plan B).

### 3.5 Eggs deposited at TARGET patch (new behaviour)

Replace the existing egg deposit at `lines 469–482`:

```cpp
// existing: oviposit at current cell
// new: oviposit at the target patch's centroid cell
auto patch_rc = habitat_engine.patch_centroid(soa.oviposition_target_patch[idx]);
habitat_engine.deposit_eggs(patch_rc.first, patch_rc.second, soa.eggs[idx]);
soa.eggs[idx] = 0;
soa.state[idx] = GonotrophicState::HOST_SEEKING;
```

`deposit_eggs` is a new `HabitatEngine` method — it forwards to the existing aquatic-habitat code (which already handles per-cell egg totals).

### 3.6 `habitat_engine.hpp` — new methods (cross-plan helpers)

- `int32_t patch_id_for_cell(int row, int col) const;`
- `int32_t nearest_viable_patch(int row, int col, double radius_m) const;`
- `bool is_patch_viable(int32_t patch_id) const;`
- `std::pair<int, int> patch_centroid(int32_t patch_id) const;`
- `void deposit_eggs(int row, int col, int n_eggs);`

All new. Plan A's `nearest_viable_cell` (Coord-based) is the building block for `nearest_viable_patch` (patch-id-based).

### 3.7 New helper `gaussian_step_kernel`

In a new `dispersal_kernels.hpp`:

```cpp
std::pair<int, int> gaussian_step_kernel(
    std::pair<int, int> current,
    std::pair<int, int> target,
    double sigma_m,
    std::mt19937& rng
);
// 70% of step is a unit step toward target; 30% is a Gaussian-perturbed step
// (sigma=sigma_m in metres, converted to cell units internally).
```

## 4. Scorer(s) — new

| ID | File | Weight | Target | Source |
|---|---|---|---|---|
| **D16** `spread_rate` | `.../D16_spread_rate.py` | 0.15 | p90 in **[5, 20] km** at day 180 | Thomas 2013 |
| **D18** `site_fidelity` | `.../D18_site_fidelity.py` | 0.10 | **Fraction of eggs deposited at the natal patch** in **[0.6, 0.8]** | Depinay 2004; North & Godfray 2018 |

D1 reused.

D17 (host-clustering, Plan B's signature) is **not** added here — Plan C's spatial signature is patch-bound, not village-bound. If the orchestrator integration later combines B and C, both D17 and D18 should be added.

## 5. F1.e parity removal — required file touches

(Same as Plan A. The implementing agent must do F1.e first.)

| File | Lines | Action |
|---|---|---|
| `mal-core/src/mal_core/abm/README.md` | 19–22, 137–139 | Update F1.e language |
| `docs/perf-cpp-abm-plan.md` | 14, 68, 89, 152, 201, 266, 289, 431, 446–448, 499, 501 | Update F1.e language |
| `mal-core/src/mal_core/abm/tests/test_abm_fast_parity.py` | whole | Delete |
| `mal-ghana-sim/tests/test_abm_fast_parity.py` | whole | Delete |

## 6. Risks

1. **`patch_id_for_cell` performance**: if the patch list is large (>10⁴ patches), this is O(N) per emergence. Mitigation: build a cell-to-patch lookup at AOI load time; document in `habitat_engine.hpp`.
2. **Natal patch destroyed mid-run**: a 300 m habitat removal at the natal patch (Yang 2009) will reduce D18 below 0.6 because the female is forced to use the fallback. *This is the correct behaviour* — D18 should dip when the habitat is removed. Document in the scorer.
3. **D18 score variance across seeds**: a Bernoulli sample of u ~ U(0,1) for each mosquito produces high seed variance at small populations. Mitigation: D18 is computed over the full 180-day run, not a single day; this is enough n for stable estimates.
4. **Walk kernel determinism**: the `gaussian_step_kernel` is stochastic; seeded RNG must be threaded through correctly. Re-record 2–3 regression snapshots.
5. **Migration between Plan A's windborne and Plan C's site fidelity**: if a windborne migrant changes `natal_patch_id` mid-life, the target flips. **Do not change `natal_patch_id` after emergence.** Document this constraint in `mosquito_state.hpp`.

## 7. Files modified

- `mal-core/src/mal_core/abm/src/mosquito_state.hpp` (2 new SoA fields)
- `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` (emergence lines 396–425; oviposition deposit lines 469–482; new OVIPOSITION_SEEKING branch in gonotrophic loop lines 434–519)
- `mal-core/src/mal_core/abm/src/habitat_engine.hpp` (5 new methods)
- `mal-core/src/mal_core/abm/src/dispersal_kernels.hpp` (new)
- `mal-core/src/mal_core/abm/src/gonotrophic_cycle.hpp` (no enum change; OVIPOSITION_SEEKING is already there)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D16_spread_rate.py` (new)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D18_site_fidelity.py` (new)
- `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` (D16, D18)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py` (weights)
- `mal-core/src/mal_core/abm/README.md` (F1.e)
- `docs/perf-cpp-abm-plan.md` (F1.e)
- `mal-core/src/mal_core/abm/tests/test_abm_fast_parity.py` (delete)
- `mal-ghana-sim/tests/test_abm_fast_parity.py` (delete)

## 8. Effort estimate

| Phase | Sessions |
|---|---|
| F1.e removal (safe-first) | 0.3 |
| D16 + D18 scorers + thresholds | 0.4 |
| `natal_patch_id` + emergence set | 0.3 |
| OVIPOSITION_SEEKING return-decision + walk | 0.6 |
| `deposit_eggs` + new HabitatEngine methods | 0.3 |
| Run fast suite, tune, 30/180-day sims | 0.1 |
| **Total** | **~2.0** |

## 9. Acceptance criteria

- [ ] `pytest -m fast -v` passes; D1 ≥ 0.70, D16 ≥ 0.70, D18 ≥ 0.60, no scorer regresses > 0.05 vs baseline.
- [ ] Day-180 Ghana sim: `spread_p90_km` ∈ **[5, 20]**, `fraction_eggs_at_natal` ∈ **[0.6, 0.8]**.
- [ ] Habitat-removal stress test (zero out 300 m patch, re-run 180 days): D18 dips below 0.6 in the affected area (correct behaviour).
- [ ] CMake C++ tests pass; no new compiler warnings.
- [ ] Composite score ≥ 0.70.
- [ ] `gitagent propose --agent plan-c` succeeds with confidence ≥ 0.80.

## 10. Comparison to other plans (cross-link)

| Axis | Plan A | Plan B | Plan C (this) |
|---|---|---|---|
| Mechanism | Wind (passive) | Host-seeking (active) | Oviposition-site (active) |
| New state | none | `HOST_APPROACH` wired | `natal_patch_id` field |
| Spatial signature | Smooth radial front | Clustered around villages | Clustered around natal/ovip patches |
| New scorers | D16 | D16, D17 | D16, D18 |
| Risk | Low | Med | Med |
| Sessions | 1.5 | 3 | 2 |

Plan C is the **strongest fit** if the field data shows *patch-bound* clusters rather than *village-bound* clusters. The two are correlated (villages sit near aquatic patches) but distinguishable in high-resolution surveys. Run `mal-data-explorer/03_map_ghana.py` to see which signature matches the empirical georeferenced case data.
