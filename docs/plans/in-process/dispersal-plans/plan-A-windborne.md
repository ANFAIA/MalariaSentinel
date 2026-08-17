# Plan A — Windborne Boost (status quo + parameter + viability tweaks)

| Field | Value |
|---|---|
| **Plan ID** | A |
| **Status** | proposed |
| **Hypothesis** | Tuning the existing windborne-migration mechanism to be slightly more frequent, slightly longer, slightly more survivable, and gated by destination habitat viability, is the minimal change that broadens the spatial spread enough to match observed *Anopheles* front-wavelengths without changing the dispersal algorithm. |
| **Risk class** | Low — parameter + 1 helper. No state-machine changes. |
| **Effort** | 1.5 sessions |
| **Owner (TBD)** | `wt/plan-a-windborne` → branch `common/abm-plan-a` |

---

## 1. Biological hypothesis

Field mark-release-recapture (MRR) of *Anopheles gambiae* sensu lato in West African villages consistently shows **net outward displacement of 350–650 m/day** in the absence of strong wind, with longer tails up to ~1.5–2 km in single nights (Costantini 1996; Thomas 2013). The current ABM's `adult_dispersal` path uses a windborne boost that fires at probability `WIND_MIGRATION_PROB = 0.05` per adult per day, displacing a mosquito by one 200 m grid step in the prevailing wind direction, surviving with probability `WIND_SURVIVAL = 0.85`. This produces too few long-distance moves and too much retention around the natal patch.

We hypothesise that the **long-distance tail of the dispersal kernel is correct in shape but too thin and too lethal**. Doubling the daily migration probability, extending the flight from 4 h to 6 h (matching Huestis 2019's 6–11 h wind-supported flight durations), and raising the in-flight survival to 0.90 will put the simulated 90th-percentile displacement at day 180 into the empirically-observed 1–2 km band. A viability check on the destination cell prevents a known artifact: windborne migrants currently landing on dry or low-TWI cells continue to oviposit and survive, artificially seeding populations where the habitat model says they should die.

## 2. Literature basis

| Source | File | Key numbers used |
|---|---|---|
| **Costantini et al. 1996** | `papers/anopheles-dynamics/costantini-1996-anopheles-density-survival-dispersal.md` | 350–650 m/day outward displacement in MRR; daily survival ~0.85; supports 6 h flight. |
| **Thomas et al. 2013** | `papers/anopheles-dynamics/thomas-2013-anopheles-gambiae-gambia-dispersal.md` | Negative-exponential kernel: median 386 m, p90 1.28 km, p95 1.67 km. Half-Cauchy alt: 295 m / 1.64 km / 2.83 km. These are the targets for D16. |
| **Huestis & Lehmann 2019** | `../m7-6-wind-dispersal-plan.md` | Windborne *Anopheles* can move 100s of km in 6–11 h sustained flight; supports 6 h default and 0.90 in-flight survival. |
| **Depinay et al. 2004** | `papers/anopheles-dynamics/depinay-2004-anopheles-simulation-model.md` | Site fidelity to natal habitat is a real behaviour; wind overrides it for the long tail. |
| **North & Godfray 2018** | (cited in dispersal-kernel-calibration.md) | Settlement-to-settlement dispersal with d=0.01 sets the lower bound for D16. |
| **Yang et al. 2009** | `docs/dispersal-kernel-calibration.md` | 300 m habitat removal → 94 % reduction in local *Anopheles* density; supports the destination viability check. |

## 3. Code changes

### 3.1 Parameter tuning in `wire.hpp`

```cpp
// wire.hpp  (constexpr block ~ line 41-58; verify against current file)
constexpr double WIND_MIGRATION_PROB = 0.10;   // was 0.05
constexpr int    WIND_FLIGHT_HOURS   = 6;      // was 4 — matches Huestis 6-11 h
constexpr double WIND_SURVIVAL       = 0.90;   // was 0.85
// ADULT_DISPERSE_PROB unchanged (0.15)
```

### 3.2 Destination viability check in `mosquito_submodel.cpp::adult_dispersal` (line 606)

After the existing `displacement` is computed but **before** the in-flight survival coin-flip and the location update, gate the move:

```cpp
// mosquito_submodel.cpp::adult_dispersal
//  - compute displacement (existing code, lines 606-660)
//  - compute proposed (row', col')
//  - NEW: viability gate
if (!habitat_engine.is_viable(row_prime, col_prime, /*twi_min=*/8.0, /*water_min=*/0.05)) {
    // no long-distance move; kill the migrant instead
    soa.alive[idx] = 0;
    soa.cause_of_death[idx] = CauseOfDeath::WindDestinationUnviable;
    return;
}
```

### 3.3 New helper `HabitatEngine::nearest_viable_cell` in `habitat_engine.hpp`

```cpp
// habitat_engine.hpp
struct Coord { int row; int col; };

Coord nearest_viable_cell(int row, int col, double radius_m = 2000.0) const;
// returns the nearest cell within radius_m of (row, col) that satisfies
// is_viable() (TWI >= 8, water_frac >= 0.05). If none, returns {-1, -1}.
// Implementation: BFS over the 4-neighborhood in cell coordinates,
// stopping at radius_m / cell_size_m.  radius_m default 2000.
```

This helper is **not called by Plan A** (Plan A only adds the *gate* in `adult_dispersal`). It is added here so the helper exists for Plans B and C; the unused function will compile out cleanly. Document the cross-plan dependency in the function docstring.

### 3.4 `is_viable` member of `HabitatEngine`

The current `HabitatEngine` exposes `TWI(row, col)` and `water_fraction(row, col)` but not a single `is_viable` predicate. Add:

```cpp
bool is_viable(int row, int col, double twi_min = 8.0, double water_min = 0.05) const {
    return TWI(row, col) >= twi_min && water_fraction(row, col) >= water_min;
}
```

## 4. Scorer(s) — new

| ID | File | Weight | Target | Source |
|---|---|---|---|---|
| **D16** `spread_rate` | `mal-core/src/mal_core/abm/tests/calibration/scorers/D16_spread_rate.py` | 0.15 | p90 displacement in **[5, 20] km** at day 180; median displacement in **[0.3, 0.8] km** | Thomas 2013 negative-exponential kernel. |

D1 (`expansion.py`) is reused as-is; no new D17/D18 scorers in Plan A.

Register D16 in `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml`:

```yaml
D16:
  min_score: 0.7
  max_delta: 0.05
  hard_floor: 0.55
```

And add to `scorers/composite.py::DEFAULT_WEIGHTS` as `"D16": 0.15` (rebalance existing weights to sum 1.0 — see composite.py for current distribution).

## 5. Required file touches

| File | Lines | Action |
|---|---|---|
| `mal-core/src/mal_core/abm/README.md` | 19–22 | Update calibration scorer language |
| `mal-core/src/mal_core/abm/README.md` | 137–139 | Drop parity test references |

The implementing agent must run the fast suite to confirm nothing breaks before starting Plan A's parameter changes.

## 6. Risks

1. **Composite regression**: doubling `WIND_MIGRATION_PROB` will inflate the local host-seeking rate per migrant, possibly over-shooting the carrying-capacity scorers (D4–D6). Mitigation: run `pytest -m fast` after each parameter change; D16 is gated behind a `max_delta` of 0.05 against the previous run.
2. **Long-tail overshoot**: `WIND_SURVIVAL = 0.90` may push p95 above 2.0 km (Thomas 2013 reports 1.67 km). Mitigation: D16's `max_delta` will fail loudly; back off to 0.875 if needed.
3. **Empty-grid runs**: in the dry-season baseline, the new viability gate will kill almost every migrant, possibly starving the windborne channel. Acceptable — that is the *intended* dry-season behaviour — but monitor `expansion.py` score.
4. **`nearest_viable_cell` unused on Plan A path**: dead code in Plan A. The compile will warn under `-Wunused-function` if the helper is not referenced; static-inline in the header to suppress.
5. **Calibration suite may be slow on day-180 runs**: D16 needs a 180-day sim. Pre-warm caches in `conftest.py` if the run exceeds the PR-gate budget.

## 7. Files modified

- `mal-core/src/mal_core/abm/src/wire.hpp` (3 constants)
- `mal-core/src/mal_core/abm/src/mosquito_submodel.cpp` (1 gate in `adult_dispersal`)
- `mal-core/src/mal_core/abm/src/habitat_engine.hpp` (1 new helper + 1 new predicate)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/D16_spread_rate.py` (new file)
- `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` (1 entry)
- `mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py` (1 weight)
- `mal-core/src/mal_core/abm/README.md` (calibration scorer language)

## 8. Effort estimate

| Phase | Sessions |
|---|---|
| D16 scorer + threshold | 0.4 |
| Parameter tune + viability gate | 0.3 |
| Run fast suite, tune to pass | 0.3 |
| 30-day + 180-day Ghana run, capture metrics | 0.2 |
| **Total** | **~1.2** |

## 9. Acceptance criteria

- [ ] `pytest -m fast -v` passes; D1 ≥ 0.70, D16 ≥ 0.70, no other scorer regresses by > 0.05.
- [ ] Day-180 Ghana simulation reports `spread_p90_km` ∈ **[5, 20]** and `spread_median_km` ∈ **[0.3, 0.8]**.
- [ ] CMake C++ tests pass; no new compiler warnings.
- [ ] Composite score ≥ 0.70.
- [ ] `gitagent propose --agent plan-a` succeeds with confidence ≥ 0.85.

## 10. Comparison to other plans (cross-link)

| Axis | Plan A (this) | Plan B | Plan C |
|---|---|---|---|
| Algorithm | Tune existing windborne | Directed walk to host | Site fidelity + walk to patch |
| New state | None | `HOST_APPROACH` wired | `natal_patch_id` |
| New helpers | `is_viable`, `nearest_viable_cell` | reuses `approach_vector` | reuses `nearest_viable_cell` |
| New scorers | D16 | D16, D17 | D16, D18 |
| Risk | Low | Med | Med |
| Sessions | 1.5 | 3 | 2 |

Plan A is the **lowest-risk baseline**; if its composite ≥ 0.7 and D16 in range, it wins on effort. If the spatial front is still too narrow, Plan B/C's behavioural change is justified.
