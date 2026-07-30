# M11 — Data Pipeline Unification

> **Status**: Planned (2026-07-30). Scope supersedes the prior `docs/unify-download-plan.md` state-of-the-union (which now lives in the KG `Operational` node `op-m11-data-pipeline-unification`).
>
> **Supersedes**: M9 "Pipeline (consolidated in mal-core)" — M11 is the unification of the data pipeline stage (download → ingest → build), which was partially completed in M9.
>
> **Followed by**: M12 — Water Datasets (`docs/plan-water-datasets-m12.md`).

## 1. Context

Three problems identified from manual pipeline audits (2026-07-29):

1. **Manifest not auto-filling.** The runner's `update_dataset()` always set `type: "time-series"` even for static datasets, and used the dataset name as a file key when `year=None`. Manual edits were needed after the wind download timed out.
2. **Loader parameter inconsistency.** Across 10 loaders: `year` vs `years`, `_fetch_daily` exposed in public signatures, `**kw` catch-alls in lambdas, `species`/`water_classes`/`threshold_pct` mixed with config, `aoi: AOI | str` everywhere instead of resolving once.
3. **C++ ABM compatibility** of the produced outputs had to be verified.

Plus two clarifications surfaced in the design discussion:

- **Annual vs time-invariant** distinction. Static loaders that take `year` (WorldPop, GLW, GHSL, Wildlife, JRC GSW) use it as a **snapshot selector**, not a **time-axis index**. The runner must distinguish these two cases.
- **Water dataset coverage gap.** Only JRC GSW `occurrence` band is currently available. No monthly water layer, no SAR-based ephemeral water, no salinity signal. Deferred to M12 with explicit linkage.

## 2. Decisions (design principles, locked)

### 2.1 Loader taxonomy

| Category | Loaders | Time dim | `year` param meaning |
|---|---|---|---|
| Truly invariant | DEM, Buildings | No | N/A |
| Single-snapshot | WorldPop, GLW, GHSL, Wildlife | No | Snapshot selector (default kwarg) |
| Annual with usable time dim | JRC GSW (kept simple in M11; expansion in M12) | No in M11 | Snapshot selector |
| Real time-series | ERA5, CHIRPS, MODIS NDVI | Yes | `years`/`months` time-axis |

### 2.2 Canonical signatures

```python
# Static + single-snapshot
def load_<dataset>_<product>(
    aoi: AOI,
    *,
    cache_dir: Path | None = None,
    # snapshot selectors stay as public kwargs with defaults:
    year: int | None = None,         # WorldPop, GLW, GHSL, JRC GSW, Wildlife
    species: str = "cattle",         # GLW only
) -> xr.DataArray:
    """Reference dataset — single tile, no temporal axis."""

# Time-series
def load_<dataset>_<product>(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,   # default: all 12
    cache_dir: Path | None = None,
) -> xr.DataArray:
    """Time-series. Returns DataArray with 'time' dim if N>1, scalar if N==1."""
```

### 2.3 Rules

- `aoi`: **always** `AOI` object (runner resolves slug via `AOI.from_slug`).
- `years`: `Sequence[int]` (never `int`) for time-series.
- `months`: `Sequence[int] | None` (None = all 12).
- `cache_dir`: always kw-only, always optional.
- **Forbidden** in public signatures: `output_path`, `**kw`, `_fetch_daily`, `water_classes`, `threshold_pct`.
- Snapshot selectors (`year`, `species`) stay as **public kwargs with defaults** — configurable across releases.
- Return: `xr.DataArray` (or `xr.Dataset` for wind).

### 2.4 DOWNLOADER dict (canonical)

```python
DOWNLOADER = {
    "name": "chirps",
    "outputs": {"rainfall": load_chirps_rainfall},
    "manifest_keys": {"rainfall": "chirps_rainfall"},
    "is_time_series": True,              # REQUIRED, explicit
    "requires_auth": ["none"],
}
```

`is_time_series` is **required explicit**. Eliminates ambiguity at JRC GSW. Drives runner behaviour and manifest `type` field.

### 2.5 Manifest schema v3

```python
def update_dataset(
    aoi: str,
    dataset_name: str,
    year: int | None,
    filename: str,
    *,
    type: str,                              # "static" | "time-series" — REQUIRED
    required_for_abm: bool = False,
    variables: list[str] | None = None,     # multi-band (env tensor)
    format: str | None = None,
) -> Path:
```

**Layout:**

- Static: `{"files": {"": filename}}` (empty-string key, stable, no conflict with year strings).
- Time-series: `{"files": {str(year): filename}}`.

**Removed:** `expected_files` (computed on-the-fly when needed).

**`validate_completeness(aoi)`:** checks only entries with `required_for_abm=True`.

### 2.6 Runner — vectorized, single save point

```python
def run_one(spec, output_name, aoi, years, months, output_dir, cache_dir):
    func = spec["outputs"][output_name]
    is_ts = spec["is_time_series"]

    if is_ts:
        result = func(aoi=aoi, years=years, months=months, cache_dir=cache_dir)
        for year in years:
            sel = result.sel(time=result.time.dt.year == year)
            for month in months:
                slc = sel.sel(time=sel.time.dt.month == month)
                path = _standard_path(aoi, output_name, year, ext)
                save_product(slc, path)
                update_dataset(aoi, spec["manifest_keys"][output_name], year, path.name,
                               type="time-series", required_for_abm=spec.get("required_for_abm", True))
    else:
        result = func(aoi=aoi, cache_dir=cache_dir)
        path = _standard_path(aoi, output_name, None, ext)
        save_product(result, path)
        update_dataset(aoi, spec["manifest_keys"][output_name], None, path.name,
                       type="static", required_for_abm=spec.get("required_for_abm", True))
```

- **No inspect filter** for kwargs — canonical signature + DOWNLOADER dict fields.
- **Vectorized**: full `years`/`months` list passed in one call (not N calls).
- Runner splits result by `(year, month)` and saves one file per slice.
- `wind_6hourly` returns `xr.Dataset` with `valid_time` dim — writer handles; runner splits on `valid_time.dt.year/month`.

### 2.7 Snapshot selector vs time-axis (decision)

For static loaders with a `year` kwarg (JRC GSW, WorldPop, GLW, GHSL, Wildlife):
- `year` is **public kwarg with default** (e.g. `year=2019`).
- Runner treats them as `is_time_series=False`.
- Manifest `type="static"`, file key `""`.
- Snapshot year is **not** tracked in the manifest `files` keys — only the file itself.

Configurability rationale: when WorldPop 2024 ships, `load_worldpop_population(aoi, year=2024)` works without editing a module constant.

## 3. Execution phases

### Phase 0 — Already shipped (commits `524fccc`, `0ff4844`, `043a3f4`)

- 5 loaders refactored class→function: `worldpop`, `glw`, `ghsl`, `wildlife`, `buildings`. `DOWNLOADER` dicts added.
- Registry updated: `worldcover` removed, 5 new added.
- `worldcover.py` archived to `mal-commonlib/src/mal_commonlib/data/loaders/_legacy/`.
- CLI: `malariasim ingest --what {env,hosts,mobility,all}`.
- Pipeline stages: `BUILD_HOSTS`, `BUILD_MOBILITY` added.
- Ingest modules created: `env.py`, `hosts.py`, `mobility.py` in `mal-core/src/mal_core/ingest/`.
- Writer module created: `mal-core/src/mal_core/download/writer.py` (DataArray→COG, Dataset→NC).
- Spec docs updated: `download-api-spec.md`, `data-format-spec.md`.
- Integration bugs fixed: AOI object pass-through, ABM wrapper `run` subcommand, env.py string resolution.
- Manifest keys fixed: `env`/`habitat`, `mobility_day`/`mobility_night`/`livestock_mobility`.

### Phase 1 — Loader API unification (the strategic refactor)

**Scope:**
- Apply canonical signatures to **all 10 loaders**.
- Remove `output_path` from remaining 5 (era5, chirps, dem, modis, jrc_gsw).
- Remove `**kw`, `_fetch_daily`, `water_classes`, `threshold_pct` from public signatures.
- Move snapshot selectors to module constants where appropriate (or keep as kwargs per §2.7).
- Add `is_time_series: bool` to every `DOWNLOADER` dict.
- Tests: update signatures, drop kwargs that no longer exist.

**Acceptance:**
- `inspect.signature(load_<x>)` matches canonical pattern across all 10.
- All `DOWNLOADER["is_time_series"]` is explicit `True` or `False`.
- Tests pass: `uv run pytest mal-commonlib/tests/ -v --tb=short` (≥95% pass; pre-existing bugs tolerated).

### Phase 2 — Runner rewrite

**Scope:**
- Drop inspect-filter for kwargs (canonical signature only).
- Vectorized: full `years`/`months` list to time-series loaders.
- Time-series detection from `DOWNLOADER["is_time_series"]` (not signature).
- Runner splits result by `(year, month)`, saves N×12 files for time-series.
- Add `save_product()` call (already in `writer.py`).

**Acceptance:**
- Single loader call per (output, year-range) regardless of file count.
- N years × 12 months → N×12 GeoTIFF files on disk (or N×12 NetCDF for wind).
- Manifest registration uses `type` from DOWNLOADER dict, not signature.

### Phase 3 — Manifest v3

**Scope:**
- `update_dataset()` requires `type` field (no default; explicit).
- Layout separated: static uses `""` key, time-series uses year string.
- `required_for_abm` field for ABM completeness check (default `False`, `True` for env/habitat/host_static/wind/mobility_*).
- `variables` field for env tensor (water_frac, rainfall, temp_suitability, ndvi).
- `validate_completeness(aoi)` checks only `required_for_abm=True` entries.

**Acceptance:**
- `update_dataset(aoi, name, year, fname)` without `type=` raises `TypeError`.
- `validate_completeness("ghana")` returns `True` for fresh-download AOI (no manifest migration step).

### Phase 4 — E2E pipeline test (year 2024)

**Scope:**
- Run the full pipeline for year 2024: download → ingest → build_hosts → build_mobility → ABM.
- Command: `malariasim run --stages download,ingest,build_hosts,build_mobility,abm --aoi ghana --year 2024 --month 6` (June = peak malaria season in Ghana).
- Verify the C++ ABM binary reads all four output types cleanly:
  - env `.tif` (4-band COG) → `read_env_tif`
  - host_static `.nc` → host_landscape reader
  - habitat `.gpkg` → HabitatEngine
  - mobility `.csr` → MobilitySchedule
- Verify the ABM simulation runs end-to-end without silent errors:
  - Adult density > 0 (no collapsed-population silent failure)
  - No NaN / Inf in any output band
  - Stderr clean (no uncaught GDAL warnings, no missing-file silent fallbacks)
  - Suitable habitat count matches expectation (not 0 or all-cells)
- **No manifest migration step**: Phase 3 produces v3 schema directly; fresh downloads write into v3 without an upgrade script.
- Issue `--wind-field` in C++ binary (currently not implemented) as a follow-up ticket — out of M11 scope.

**Acceptance:**
- `malariasim run ... --year 2024 --month 6` exits 0 with all expected outputs in `runs/`.
- C++ binary reads all 4 output types without GDAL warnings.
- ABM output bands within expected ranges; no silent failures detected.
- Manifest v3 schema validated by the e2e run itself.

## 4. Cross-milestone linkage

```
M11 (this plan)                    M12 (water datasets)
──────────────────                 ────────────────────
10 existing loaders         →      +4 new water loaders
JRC GSW annual static      →      +DSWX-S1 climatology + rolling window
Manifest v3 (type,          →     +water stack composite
required_for_abm)                 +D12 scorer against 24 larval sites
Runner vectorized           →     +water stack assembly
```

**Explicit references:**
- §5 (Phase 5) points to `docs/plan-water-datasets-m12.md` for water layer scope.
- Phase 4 (manifest v3 stability) is a prerequisite for M12's water stack assembly.
- §2.4 `is_time_series` flag is designed to accommodate DSWX-S1 climatology (one product, two views).

## 5. Out of scope (deferred)

| Item | Deferred to | Reason |
|---|---|---|
| 4 new water loaders (hydrolakes, hydrorivers, worldcover, opera_dswx_s1) | **M12** | Bigger refactor; needs manifest v3 stable; salt/fresh coastline layer; D12 scorer |
| C++ binary `--wind-field` argument | Backlog | Scope C++ (`mal-abm-fast/`), not Python |
| CDS request parallelization for wind_6hourly | Backlog | Rate-limit safety first; sequential OK for v1 |
| Per-region adapter (multi-AOI) | M7+ | Beyond M11 scope |

## 6. Pitfalls and risks

1. `era5.wind_6hourly` returns `xr.Dataset` (not DataArray). Writer handles both. Runner splits on `valid_time.dt.year/month`, not `time`.
2. CDS rate limits: wind_6hourly N requests in loop. Sequential OK for v1, parallelize later.
3. Static loaders with year kwargs (JRC GSW, WorldPop, GLW, Wildlife): `year` is snapshot selector, NOT time-axis. Manifest `type="static"`, file key `""`.
4. **E2E 2024 silent failures**: ABM may produce wrong output without raising. Phase 4 acceptance includes value-range checks, NaN/Inf scans, and stderr-clean assertion to catch silent regressions (population collapse, missing-file fallbacks, NaN propagation).
5. M12 dependency: manifest v3 must be stable and deployed before M12 starts (M12's `load_water_stack()` relies on `is_time_series` + `required_for_abm`).

## 7. Acceptance criteria (milestone-level)

M11 is **done** when:

- [ ] All 10 loaders conform to canonical signature (§2.2).
- [ ] All 10 `DOWNLOADER` dicts have explicit `is_time_series`.
- [ ] Runner is vectorized, single save point, no inspect filter.
- [ ] `update_dataset()` requires `type` field.
- [ ] `validate_completeness("ghana")` passes after Phase 4 e2e run.
- [ ] C++ ABM binary reads all 4 output types (.tif, .gpkg, .nc, .csr) without warnings.
- [ ] Tests: `mal-commonlib`, `mal-core`, `mal-execution` suites ≥95% pass.
- [ ] KG node `op-m11-data-pipeline-unification` summary reflects "DONE" with commit SHAs.
- [ ] GitHub milestone M11 closed; issues moved to Done with commit references.

## 8. References

- `docs/data-format-spec.md` — manifest schema reference (to be updated to v3).
- `docs/download-api-spec.md` — loader API reference (to be updated for `is_time_series`).
- `docs/unify-download-plan.md` — prior state-of-the-union (superseded by this plan).
- `docs/plan-water-datasets-m12.md` — M12 stub, link to this plan.
- KG `Operational` node: `op-m11-data-pipeline-unification` (this plan).
- KG `Operational` node: `op-m9-pipeline-consolidated` (prior state, partially complete).
- KG `Operational` node: `op-m12-water-datasets` (next milestone, stub).

## 9. Change log

| Date | Author | Change |
|---|---|---|
| 2026-07-30 | supervisor | Initial plan, consolidating 3 prior design discussions (manifest/loader, time-series vs static, water datasets). |