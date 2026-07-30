# M12 — Water Datasets (STUB)

> **Status**: Stub (2026-07-30). Full plan to be drafted when M11 ships.
>
> **Predecessor**: M11 — Data Pipeline Unification (`docs/plans/completed/m11-pipeline-unification.md`).
>
> **Scope (preview only)**: 4 new water loaders + composite `load_water_stack()` + D12 calibration scorer. Detail deferred to M12 full plan when M11 acceptance criteria are met.

## Why this exists as a stub now

Three reasons to draft this stub while M11 is still in planning:

1. **M11 §4 (cross-milestone linkage)** explicitly references M12 — the stub makes that pointer resolvable.
2. **M11 §2.4 `is_time_series` flag** is designed to accommodate DSWX-S1 climatology (one product, two views: weekly climatology + 18-month rolling). Confirming the M12 design now prevents M11 from over-constraining it.
3. **M11 §6 risk 5** flags that M12 depends on manifest v3 stability. The stub documents that dependency.

## 1. M11 prerequisites (must be DONE before M12 starts)

- [ ] All 10 existing loaders conform to canonical signature (M11 Phase 1).
- [ ] Manifest v3 with `is_time_series`, `required_for_abm`, `variables` deployed (M11 Phase 3).
- [ ] `validate_completeness("ghana")` passes end-to-end after a real run (M11 Phase 4).
- [ ] Runner vectorized + split-by-(year, month) (M11 Phase 2).

Without these, M12's `load_water_stack()` composite has no stable foundation.

## 2. Time-variability table for the 4 new water loaders

| Dataset | Type | Cadence | Window | Role |
|---|---|---|---|---|
| `hydrolakes` | vector static | n/a | Snapshot 2016 v1.0 | Permanent lakes, vector base (~30 MB clipped Ghana) |
| `hydrorivers` | vector static | n/a | Snapshot 2013 v1.0 | Permanent rivers, vector base (~10 MB clipped Ghana) |
| `worldcover` (new addition; `_legacy/worldcover.py` already archived as water layer — see note below) | raster 10 m static | n/a | Snapshot 2021 v200 | Permanent water mask cross-check (`Permanent water bodies` class) |
| `opera_dswx_s1` | raster 30 m SAR | ~12 d (Ghana) | Climatology 2021–present (per-pixel per-week-of-year) + 18-mo rolling window | Ephemeral / seasonal water for oviposition detection |

**Explicitly excluded:** `gsw_monthly` — the 4 datasets above cover static water, big/small ponds, and seasonality on their own.

**Note on `worldcover`:** the previous M11 work archived `worldcover.py` to `mal-commonlib/src/mal_commonlib/data/loaders/_legacy/` as it was redundant with JRC GSW for the `water_frac` channel. M12 re-introduces `worldcover` **only** for its land-cover classes (mangroves, herbaceous wetland, permanent water bodies) as a static cross-check — not as the primary water signal. New loader file: `mal-core/src/mal_core/download/worldcover.py`.

## 3. Salt / fresh distinction (workaround)

No dataset in the surveyed 6 distinguishes salt vs fresh water. Workaround:

- `gsshgs_coastline` loader — GSHHG / Natural Earth 1:10 m coastline polygon (~10 MB).
- Compute `distance_to_coast_m` raster at 30 m.
- Rule: `distance_to_coast_m < 10_000` → likely brackish / salt-influenced (coastal lagoons).
- For inland Ghana this is mostly a flag, not a hard boundary.
- Future: overlay World Ocean Atlas annual salinity raster (~0.25° global) for Gulf of Guinea coast only.

## 4. Composite — `load_water_stack(aoi, date_range)`

Returns a single `xr.Dataset` with bands:

- `permanent_water_mask` — from hydrolakes + hydrorivers vector → 30 m raster (binary).
- `dynamic_water_mask` — from DSWX-S1 18-mo rolling composite (`dynamic` + `partial` classes, OR-aggregated).
- `wetland_mask` — from WorldCover `Herbaceous wetland` class (10 m, downsampled).
- `water_occurrence_climatology` — from DSWX-S1 climatology (per-week-of-year, 2021–present).
- `distance_to_coast_m` — from GSHHG coastline.
- `water_frac` — backwards-compat passthrough from JRC GSW (M11 keeps JRC GSW as the existing water source).

Stored as `<aoi>_water_stack.nc` in `data/<aoi>/`. Registered in manifest with `required_for_abm=True`, `variables=[<band names>]`, `type="static"` (it's a composite, not a time-series) — though individual band sources may be time-series.

## 5. Calibration — D12 scorer

- **Target**: 24 larval sites (KG `09b7a8bf-080f-49ac-89a7-d9d1fafca0c5`).
- **Metric**: precision / recall of `permanent_water_mask ∪ dynamic_water_mask` (mask union) over each site buffer (e.g. 250 m).
- **Acceptance**: recall ≥ 0.80 on ≥ 18 / 24 sites; precision ≥ 0.60.
- **Registered in**: `mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml` as D12 with `min_score`, `max_delta`, `hard_floor`.

## 6. Pitfalls to record (KG `Pitfall` nodes)

1. `pitfall-no-salinity-dataset` — no surveyed dataset distinguishes salt vs fresh; require distance-to-coast workaround.
2. `pitfall-dswx-short-history` — DSWX-S1 V1 only 2021+; pre-2021 oviposition baselines must come from DSWX climatology (5-year rolling window minimum) or external data.
3. `pitfall-worldcover-no-change-detection` — WorldCover 2020 v100 vs 2021 v200 algorithm drift (PVR §3.2); inter-year diff ≠ real change. Use 2021 v200 only.
4. `pitfall-worldcover-wetland-ua` — `Herbaceous wetland` User's Accuracy 30.5% globally (PVR §3.1); do not use as sole wetland signal.
5. `pitfall-coastline-10km-rule-arbitrary` — 10 km salt/fresh cutoff is a heuristic, not measured. Document explicitly.

## 7. Cross-link to M11

| M11 section | M12 dependency |
|---|---|
| §2.2 canonical signature (vectorized time-series) | DSWX-S1 climatology loader uses `is_time_series=False` (climatology is pre-aggregated, single tile) — BUT the 18-mo rolling window IS time-series. Two-product-one-loader pattern needs M11 §2.4 `is_time_series` to be flexible enough (still flag-level; may need a `dual_mode: True` later). |
| §2.5 manifest v3 (`variables` field) | `load_water_stack` registers multi-band output; relies on `variables` list to declare its 5-6 bands. |
| §2.6 runner split-by-(year, month) | Not used for water stack (it's static), but used by DSWX-S1 climatology's underlying per-week-of-year tile production. |
| §3 Phase 4 ABM compatibility | Water stack is consumed by env tensor assembly in `ingest/env.py` — must verify `.nc` is read correctly. |

## 8. Acceptance criteria (milestone-level, preview)

M12 is **done** when:

- [ ] 4 new loaders registered (`hydrolakes`, `hydrorivers`, `worldcover`, `opera_dswx_s1`) with `DOWNLOADER` dicts.
- [ ] `load_water_stack(aoi, date_range)` returns composite Dataset.
- [ ] `gsshgs_coastline` loader + `distance_to_coast_m` raster generated.
- [ ] D12 scorer registered with thresholds; runs against 24 larval sites; precision/recall hit acceptance.
- [ ] 4-5 pitfalls recorded in KG.
- [ ] KG node `op-m12-water-datasets` summary reflects "DONE" with commit SHAs.
- [ ] Manifest v3 handles multi-band composite output cleanly.

## 9. References

- `docs/plans/completed/m11-pipeline-unification.md` — M11 plan (predecessor).
- KG `Operational` node: `op-m11-data-pipeline-unification`.
- KG `Operational` node: `op-m12-water-datasets` (this plan, stub).
- Datasets surveyed: JRC GSW, Copernicus WB 100m, OPERA DSWX-S1, Sentinel-1 RTC (HyP3), HydroLAKES, HydroRIVERS, ESA WorldCover 2021 v200. Excluded: Copernicus WB (too coarse), HyP3 RTC (not a water product).

## 10. Change log

| Date | Author | Change |
|---|---|---|
| 2026-07-30 | supervisor | Stub created, linking to M11. Full plan deferred until M11 ships. |