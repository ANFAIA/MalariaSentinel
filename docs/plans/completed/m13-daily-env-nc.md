# M13 — Daily Env NC + Dynamic Water Pipeline

> **Status**: Stub (2026-07-30). Full plan to be drafted when M11 ships.
>
> **Predecessor**: M11 — Data Pipeline Unification (`docs/plans/completed/m11-pipeline-unification.md`).
>
> **Followed by**: M12 — Water Datasets (`docs/plans/in-process/m12-water-datasets.md`). M13 runs **before** M12 because M12's DSWX-S1 climatology + 18-month rolling window write into the same daily NC infra that M13 builds.
>
> **Scope (preview only)**: Per-output `output_format` in DOWNLOADER + writer split (TIF for monthly, NC for daily multi-year) + refactor `load_chirps_rainfall_daily` to canonical `(years, months)` signature + manifest v3 schema update for multi-year NC files + `env.py --format nc` legacy deprecation + daily env NC generator command. Detail deferred to M13 full plan when M11 acceptance criteria are met.

## Why this exists as a stub now

Four reasons to draft this stub while M11 is still in planning:

1. **M11 §1 / Gap 1 discovered during M11 execution**: `load_chirps_rainfall_daily` not refactored to canonical signature (commit `3baac53`). Runner passes `years`/`months` to ALL time-series outputs → TypeError on chirps downloader. User review (2026-07-30) revealed this is not a simple signature gap: `.nc` is the **new** canonical daily env format, the runner's per-month `.tif` slicing cannot represent daily 3D arrays, and PLUVIAL_POOL dynamic rule in the ABM (`wire.hpp:140-153`) requires daily rainfall to detect ephemeral breeding sites.
2. **M11 §2.4 `is_time_series` flag** is a binary scalar. M13 needs **per-output temporal granularity** (`monthly` | `daily`) which is finer. Cannot be folded into `is_time_series` without losing the binary clarity M11 locked in §2.4.
3. **M11 §3 Phase 4** runs E2E on a single year/month (`--year 2024 --month 6`). Multi-year daily NC output is out of M11 scope by design. M13 extends to multi-year daily.
4. **M12 §7 cross-link**: DSWX-S1 18-month rolling window is a daily-cadence product (climatology uses pre-aggregated tiles, but the rolling window is daily). M12's `load_water_stack()` and DSWX-S1 loader need the per-output `output_format="nc"` machinery that M13 ships.

## 1. M11 prerequisites (must be DONE before M13 starts)

- [ ] All 10 existing loaders conform to canonical signature (M11 Phase 1).
- [ ] Manifest v3 with `is_time_series`, `required_for_abm`, `variables` deployed (M11 Phase 3).
- [ ] `validate_completeness("ghana")` passes end-to-end after a real run (M11 Phase 4).
- [ ] Runner vectorized + split-by-(year, month) for monthly outputs (M11 Phase 2).

Without these, M13's per-output format split has no stable foundation.

## 2. Two CHIRPS loaders — why both, and how M13 reconciles them

| Function | Output | Returns | Used by |
|---|---|---|---|
| `load_chirps_rainfall` | monthly aggregate mm | 2D (y, x) for single (year, month); 3D (time=months, y, x) for multi-month | legacy `--format tif` env path → 4-band COG (one band = "rainfall"); monthly aggregate, no daily dynamics |
| `load_chirps_rainfall_daily` | daily mm/day | 3D (time=days, y, x), n_days per month | new `--format nc` daily env path → NetCDF with per-day rainfall slice; feeds PLUVIAL_POOL dynamic rule in ABM |

Both needed because the ABM has two env readers with different biological use-cases:

- `read_env_tif` (`env_reader.hpp:60`) → static 4-band COG (water_frac, rainfall, temp_suitability, ndvi). Rainfall here is monthly mm, not daily → cannot drive per-day PLUVIAL_POOL rule.
- `read_env_nc` (`env_reader.hpp:87`) → `DailyEnvBands` with `n_days * h * w` for rainfall, water_temp_c, water_frac, ndvi. Each day = one time slice → PLUVIAL_POOL rule fires per day.

**Biological justification for NC** (`wire.hpp:140-153`):

```
// PLUVIAL_POOL dynamic-patch rule:
//   cell (r, c) is a habitat patch today iff
//       TWI(r, c) >  PLUVIAL_POOL_TWI_THRESHOLD
//       water_frac(r, c) > PLUVIAL_POOL_WATER_FRAC_MIN  (strictly > 0)
//       rain_d(r, c) >  PLUVIAL_POOL_RAIN_THRESHOLD_MM   (= 15 mm/day)
//
// Rationale for 15mm (was 50mm): Ghana's rainy season averages 5-15mm/day,
// so 50mm was almost never reached and the rule rarely activated. 15mm is
// the biological threshold for ephemeral pool formation. Also, daily rain
// >40mm correlates NEGATIVELY with larval density (heavy rain washes larvae
// out of pools), so 50mm was biologically counterproductive as well.
```

Without daily NC, PLUVIAL_POOL collapses to "rain > 15mm this month" — a constant flag for the whole month. Defeats the purpose of dynamic ephemeral-pool detection.

**`coordinator.cpp:80-93` confirms**:

```
// Pre-existing habitat patches are always activated. They
// represent permanent water features (rivers, lakes, wetlands)
// identified at habitat-engine build time, NOT ephemeral
// pluvial pools that come and go with daily rain. The
// PLUVIAL_POOL_RAIN_THRESHOLD_MM rule below still gates the
// dynamic ephemeral-pool rule (cells satisfying
// twi > THRESHOLD AND water_frac > MIN AND rain > 50 mm/day).
```

Existing gpkg patches = permanent water. PLUVIAL_POOL = ephemeral water detected from daily rain. Both layers active in the same cell when conditions overlap.

## 3. Decisions (design principles, preview)

### 3.1 Per-output `output_format` flag

DOWNLOADER dict gets a new per-output field. Two-value enum: `monthly` (TIF) or `daily` (NC).

```python
DOWNLOADER = {
    "name": "chirps",
    "is_time_series": True,        # M11 §2.4 — binary flag, kept
    "outputs": {
        "rainfall":       (load_chirps_rainfall, "monthly"),
        "rainfall_daily": (load_chirps_rainfall_daily, "daily"),
    },
    "formats": {                   # M13 — per-output temporal granularity
        "rainfall":       "monthly",
        "rainfall_daily": "daily",
    },
    "manifest_keys": {
        "rainfall":       "chirps_rainfall",
        "rainfall_daily": "chirps_rainfall_daily",
    },
}
```

Rationale: keeps M11 §2.4 `is_time_series` binary for backward compatibility + runner dispatch. Adds per-output `formats` for writer/manifest selection.

### 3.2 `load_chirps_rainfall_daily` canonical signature

Refactor to match M11 §2.2 canonical time-series pattern:

```python
def load_chirps_rainfall_daily(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,     # None = all 12
    cache_dir: pathlib.Path | None = None,
    _fetch_daily: Callable[[int, int, int], xr.DataArray] | None = None,  # testing hook, kw-only
) -> xr.DataArray:
    """Returns DataArray with (time=days, y, x) spanning years × months."""
```

Loop year × month. Per month: existing inner day-loop (fetch + reproject + concat). Final concat along `time` with per-day `cftime.DatetimeGregorian` coords. If years × months = single month → still returns 3D (n_days, y, x), distinct from `load_chirps_rainfall` 2D return.

### 3.3 Runner — split per output_format

Two paths in `runner.run_download`:

- **`monthly`** (current M11 behaviour): sel month → 2D slice → `rio.to_raster` per (year, month) → N×12 TIF files. Manifest `files: {year: filename}` per year.
- **`daily`** (M13 new): no slicing — entire 3D time-series written as ONE NetCDF per downloader-output. File: `<aoi>_<product>_<year_start>_<year_end>_env.nc` (e.g. `ghana_chirps_rainfall_daily_2024_2025.nc`). Manifest registers this single file with `period: {start, end}` metadata. Writer uses `to_netcdf` not `rio.to_raster`.

For M13 the daily path is single-file multi-year. Future M12 DSWX-S1 may want per-month daily files (since 12-day cadence). Defer that decision to M12 with a follow-up ticket if needed.

### 3.4 Manifest v3.1 — multi-year NC entries

Extend manifest v3 to register a single NC file spanning N years:

```python
def update_dataset(
    aoi: str,
    dataset_name: str,
    year: int | None,                   # year = None for multi-year NC entries
    filename: str,
    *,
    type: str,                          # "static" | "time-series" — M11
    required_for_abm: bool = False,     # M11
    variables: list[str] | None = None, # M11
    format: str | None = None,          # M11 ("tif" | "nc" | "gpkg" | "csr")
    period: dict[str, str] | None = None,  # M13 — {"start": "2024-01-01", "end": "2025-12-31"}
) -> Path:
```

`validate_completeness("ghana")` updated: for `rainfall_daily` entry, check that `period.start` and `period.end` cover the requested AOI time-range, not individual year keys.

### 3.5 `env.py --format nc` path → deprecated

Current `mal-core/src/mal_core/ingest/env.py` has `output_format: 'tif' | 'nc'` parameter and `_write_env_nc()` legacy NetCDF writer. M13:

1. Mark `output_format='nc'` as deprecated. Raise `DeprecationWarning` if invoked.
2. Remove the `nc` branch in `build_env_tensor` (lines 352-382). Keep only `tif` branch.
3. Remove `_write_env_nc()` function (lines 149-246).
4. Add migration note in `agents/skills/mal-execution-api/SKILL.md`: legacy daily NC is now produced by the runner via `malariasim download --outputs rainfall_daily --years 2024,2025`.

Future removal: M14+ (out of scope for M13).

### 3.6 ABM `read_env_nc` consumption — unchanged

M13 does NOT modify `env_reader.hpp` or `climate.hpp`. The existing `read_env_nc(path, max_days)` reads multi-day `DailyEnvBands`. M13's runner-produced NC matches the format that `_write_env_nc()` used (`xarray.to_netcdf()` with CF-1.8 conventions, UNLIMITED time dim, vars `rainfall`, `water_temp_c`, `water_frac`, `ndvi`). Verify by reading one of the existing legacy NC files (`scripts/build_2year_nc.py:21`) and confirming variable names + dimensions match what `read_env_nc()` expects.

## 4. Phases (preview)

### Phase 1 — DOWNLOADER schema + chirps_daily refactor (test-driven)

- Refactor `load_chirps_rainfall_daily` signature per §3.2.
- Update `DOWNLOADER["formats"]` field in `chirps.py` + add to registry `DownloaderSpec`.
- Add tests in `mal-commonlib/tests/test_chirps.py`:
  - `test_chirps_daily_single_month`: `years=[2024], months=[6]`, expect shape `(30, h, w)` and time coords `2024-06-01..2024-06-30`.
  - `test_chirps_daily_multi_month`: `years=[2024], months=[6, 7]`, expect shape `(61, h, w)` with correct calendar days (June 30 + July 31).
  - `test_chirps_daily_signature_canonical`: `inspect.signature` matches M11 §2.2 pattern (no `output_path`, no `**kw`, kw-only `cache_dir`).

### Phase 2 — Runner split per output_format

- `runner.py` reads `spec.formats[output_name]` to dispatch.
- New `monthly` path: existing M11 Phase 2 logic (unchanged).
- New `daily` path: single NC writer using `xarray.to_netcdf()`, registers with `period` metadata.
- `writer.py` gains explicit `format: "tif" | "nc"` parameter; refuses to write 3D DataArray via `rio.to_raster` (clear error: "3D DataArray requires NC writer, not TIF writer").

### Phase 3 — Manifest v3.1 schema

- `manifest.py` `update_dataset()` adds `period` kwarg.
- `validate_completeness(aoi)` extended to check `period` coverage for daily NC entries.
- Document in `docs/specs/data/spec.md`.

### Phase 4 — env.py deprecation + final E2E

- Add `DeprecationWarning` for `output_format='nc'`.
- Remove `_write_env_nc` function.
- Update `agents/skills/mal-execution-api/SKILL.md` with migration note.
- E2E test: `malariasim download --datasets chirps --outputs rainfall_daily --years 2024,2025 --aoi ghana` → produces `ghana_chirps_rainfall_daily_2024_2025.nc` (~ X MB for 731 days × 429K cells × 4 bytes = ~1.2 GB uncompressed). Then `malariasim run --stages abm --env data/ghana/ghana_chirps_rainfall_daily_2024_2025.nc --aoi ghana` → C++ ABM reads via `read_env_nc`, runs end-to-end.

## 5. Pitfalls to record (KG `Pitfall` nodes)

1. `pitfall-runner-monthly-slicing-breaks-daily` — `runner.py` per-month slice + `rio.to_raster` fails on 3D (time, y, x). Fix: per-output `formats` flag.
2. `pitfall-pluvial-pool-needs-daily-rain` — TIF monthly env cannot drive PLUVIAL_POOL rule (rain > 15mm/day undefined on monthly aggregate). M13's daily NC fixes this. Without M13, ephemeral pool detection is broken.
3. `pitfall-legacy-env-nc-deprecation` — `env.py --format nc` is the old way. Users must migrate to runner-based NC generation. Document migration path.
4. `pitfall-daily-nc-storage` — uncompressed multi-year daily NC for 1km Ghana = ~1.2 GB. May need compression (`zlib` level 5 ≈ 4× reduction → ~300 MB) or chunking. Defer to M14 if perf becomes a concern.

## 6. Cross-link to M11 / M12

| M13 section | Dependency |
|---|---|
| §3.2 `load_chirps_rainfall_daily` signature | Builds on M11 §2.2 canonical time-series signature. |
| §3.3 Runner split | Extends M11 §2.6 runner — adds per-output format dispatch on top of M11's per-output time-series dispatch. |
| §3.4 Manifest v3.1 | Extends M11 §2.5 manifest v3 with `period` field for multi-year NC entries. |
| §3.5 env.py deprecation | Removes legacy parallel path that M11 §1 surfaced as Gap 1. |
| **M12 §2 DSWX-S1 climatology + rolling window** | DSWX-S1 18-month rolling window writes into the same `daily` NC infra M13 ships. M12 inherits `formats: "daily"` machinery. |
| **M12 §4 `load_water_stack()` composite** | Could write dynamic_water_mask into the daily NC env as a 5th variable. M13 manifest v3.1 must allow `variables` list to extend beyond the M11 4-band env tensor. |

## 7. Acceptance criteria (milestone-level, preview)

M13 is **done** when:

- [ ] `load_chirps_rainfall_daily` signature matches M11 §2.2 canonical pattern. Tests pass.
- [ ] DOWNLOADER dict exposes `formats` per output. Registry `DownloaderSpec` carries the field.
- [ ] Runner writes daily outputs as single multi-year NC files via `xarray.to_netcdf()`.
- [ ] Manifest v3.1 supports `period` field. `validate_completeness("ghana")` checks daily NC entries by period coverage.
- [ ] `env.py` `output_format='nc'` raises `DeprecationWarning`. `_write_env_nc` removed.
- [ ] `malariasim download --datasets chirps --outputs rainfall_daily --years 2024,2025 --aoi ghana` produces a valid NC consumable by `read_env_nc()` in C++ ABM.
- [ ] C++ ABM reads the runner-produced NC and runs end-to-end without silent errors (population > 0, no NaN/Inf, stderr clean).
- [ ] 4 pitfalls recorded in KG.
- [ ] KG node `op-m13-daily-env-nc` summary reflects "DONE" with commit SHAs.

## 8. References

- `docs/plans/completed/m11-pipeline-unification.md` — M11 plan (predecessor).
- `docs/plans/in-process/m12-water-datasets.md` — M12 stub (successor). M12 depends on M13's daily NC infra.
- `mal-core/src/mal_core/abm/include/mal_abm_fast/env_reader.hpp` — C++ ABM dual reader (TIF + NC).
- `mal-core/src/mal_core/abm/include/mal_abm_fast/climate.hpp:78-100` — `load_from_env_nc` + thread-shared daily state.
- `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp:140-153` — PLUVIAL_POOL rule rationale (15mm threshold).
- `mal-core/src/mal_core/abm/src/coordinator.cpp:80-109` — ephemeral vs permanent habitat patch distinction.
- KG `Operational` node: `op-m11-data-pipeline-unification`.
- KG `Operational` node: `op-m13-daily-env-nc` (this plan, stub).
- KG `Operational` node: `op-m12-water-datasets` (successor).

## 9. Change log

| Date | Author | Change |
|---|---|---|
| 2026-07-30 | supervisor | Stub created, linking to M11 (predecessor) + M12 (successor). Defers full plan until M11 ships. Promoted from Gap 1 (M11 §1) after user review confirmed `.nc` is the new canonical env format and PLUVIAL_POOL rule requires daily rain. |
