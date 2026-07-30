# Unify Download + Ingest + Build — State of the Union

> **Status**: COMPLETED — superseded by `docs/plans/completed/m11-pipeline-unification.md`. Historical reference only. All 12 bugs catalogued in §13 below were resolved by M11 Phases 1–4 (commits `524fccc`, `0ff4844`, `a6d3618`, `5f9e66b`, `34f7dac`, `043a3f4`, `3baac53`, `3ec8844`, `301b0b8`, `506a752`).
>
> **Purpose**: This document captured the REAL current state of the MalariaSentinel data pipeline
> as of 2026-07-29. It was given to a planning model that produced M11 — a clean,
> actionable plan for unifying the download → ingest → build pipeline.
>
> **Problem**: Had redundant code paths, inconsistent loader signatures, a broken pipeline,
> and spec-vs-reality mismatches. Resolved by M11.

---

## 1. Architecture Overview

```
mal-commonlib/          # Shared config, data loaders, AOI
mal-core/               # Pipeline logic, ABM wrapper, ingest, download runner
mal-execution/          # CLI entrypoints (malerasim command)
mal-ghana-sim/          # Ghana-specific research experiment
mal-data-explorer/      # Dataset visualization sandbox
```

**Data flow**:
```
download (fetch remote → cache) → ingest (build ABM-ready tensors) → ABM (C++ binary)
```

**Current pipeline stages** (in `mal-core/src/mal_core/pipeline/stages.py`):
```python
class Stage(str, Enum):
    DOWNLOAD = "download"
    INGEST = "ingest"
    BUILD_HOSTS = "build_hosts"
    BUILD_MOBILITY = "build_mobility"
    ABM = "abm"
    SCORING = "scoring"
    TRAINING = "training"
    PREDICTION = "prediction"
```

---

## 2. Loader Inventory — REAL Signatures

Every loader is in `mal-commonlib/src/mal_commonlib/data/loaders/`.

### 2.1 Function-style loaders (6 files)

These follow the spec's function-style pattern:

| File | Function | Signature | DOWNLOADER? | Returns |
|------|----------|-----------|-------------|---------|
| `era5.py` | `load_era5_temp_suitability` | `(aoi, year, month, *, cache_dir=None)` | Yes | `xr.DataArray` |
| `era5.py` | `load_era5_water_temp` | `(aoi, year, month, *, cache_dir=None)` | Yes | `xr.DataArray` |
| `era5.py` | `load_era5_wind_6hourly` | `(aoi, years, *, months=None, output_path=None, cache_dir=None)` | Yes | `xr.Dataset \| Path` |
| `chirps.py` | `load_chirps_rainfall` | `(aoi, *, year, month, output_path=None, cache_dir=None, _fetch_daily=None)` | Yes | `xr.DataArray` |
| `chirps.py` | `load_chirps_rainfall_daily` | `(aoi, *, year, month, output_path=None, cache_dir=None, _fetch_daily=None)` | Yes | `xr.DataArray` |
| `dem.py` | `load_merit_dem` | `(aoi, *, output_path=None, cache_dir=None)` | Yes | `xr.DataArray` |
| `modis.py` | `load_modis_ndvi` | `(aoi, *, year, month, output_path=None, cache_dir=None)` | Yes | `xr.DataArray` |
| `jrc_gsw.py` | `load_jrc_gsw_water_frac` | `(aoi, *, year=2021, month=None, output_path=None, cache_dir=None, water_classes=None, threshold_pct=...)` | Yes | `xr.DataArray` |

**Critical issue with all function-style loaders**: They accept `output_path` in their signature but
the docstring says "reserved for future use" — **they never actually save to that path**.
The `output_path` parameter is accepted and ignored.

### 2.2 Class-style loaders (5 files)

These use a class pattern, NOT function-style:

| File | Class | Public method | DOWNLOADER? | Returns |
|------|-------|--------------|-------------|---------|
| `worldpop.py` | `WorldPopLoader` | `.load(aoi, year=2019, *, cache_dir=None)` | Yes | `xr.DataArray` |
| `glw.py` | `GLWLoader` | `.load(aoi, species="cattle", *, cache_dir=None)` | Yes | `xr.DataArray` |
| `ghsl.py` | `GHSLLoader` | `.load(aoi, *, cache_dir=None)` | Yes | `xr.DataArray` |
| `wildlife.py` | `WildlifeLoader` | `.load(aoi, *, year=2021, cache_dir=None)` | Yes | `xr.DataArray` |
| `buildings.py` | `BuildingsLoader` | `.load(aoi, *, cache_dir=None)` | Yes | `xr.DataArray` |

**These also have function-style wrappers** (added in a recent refactor):

| File | Function | Signature |
|------|----------|-----------|
| `worldpop.py` | `load_worldpop_population` | `(aoi, *, year=2019, output_path=None, cache_dir=None)` |
| `glw.py` | `load_glw_livestock` | `(aoi, *, species="cattle", output_path=None, cache_dir=None)` |
| `ghsl.py` | `load_ghsl_urban_class` | `(aoi, *, output_path=None, cache_dir=None)` |
| `wildlife.py` | `load_wildlife_host_proxy` | `(aoi, *, year=2021, output_path=None, cache_dir=None)` |
| `buildings.py` | `load_buildings_fraction` | `(aoi, *, output_path=None, cache_dir=None)` |

**BUT**: The `hosts.py` ingest module still uses the CLASS-style loaders, NOT the function-style:
```python
from mal_commonlib.data.loaders.worldpop import WorldPopLoader
wp = WorldPopLoader()
pop_da = wp.load(aoi, year=worldpop_year, cache_dir=cache_dir)
```

### 2.3 Legacy loader

| File | Status |
|------|--------|
| `worldcover.py` → `_legacy/worldcover.py` | Archived. Replaced by `jrc_gsw`. |

---

## 3. DOWNLOADER Dicts — What Each Loader Exports

Every loader module exports a `DOWNLOADER` dict. Here's what each one contains:

### era5.py
```python
DOWNLOADER = {
    "name": "era5",
    "description": "ERA5 reanalysis: temperature, wind, humidity",
    "requires_auth": ["cds"],
    "outputs": {
        "temp_suitability": load_era5_temp_suitability,
        "water_temp": load_era5_water_temp,
        "wind_6hourly": load_era5_wind_6hourly,
    },
    "manifest_keys": {
        "temp_suitability": "era5_temp",
        "water_temp": "era5_water_temp",
        "wind_6hourly": "wind",
    },
}
```

### chirps.py
```python
DOWNLOADER = {
    "name": "chirps",
    "description": "CHIRPS rainfall: daily and monthly precipitation",
    "requires_auth": ["none"],
    "outputs": {
        "rainfall": load_chirps_rainfall,
        "rainfall_daily": load_chirps_rainfall_daily,
    },
    "manifest_keys": {
        "rainfall": "chirps_rainfall",
        "rainfall_daily": "chirps_rainfall_daily",
    },
}
```

### dem.py
```python
DOWNLOADER = {
    "name": "dem",
    "description": "MERIT DEM elevation",
    "requires_auth": ["none"],
    "outputs": {"elevation": load_merit_dem},
    "manifest_keys": {"elevation": "elevation"},
}
```

### modis.py
```python
DOWNLOADER = {
    "name": "modis",
    "description": "MODIS NDVI",
    "requires_auth": ["earthdata"],
    "outputs": {"ndvi": load_modis_ndvi},
    "manifest_keys": {"ndvi": "modis_ndvi"},
}
```

### jrc_gsw.py
```python
DOWNLOADER = {
    "name": "jrc_gsw",
    "description": "JRC Global Surface Water",
    "requires_auth": ["none"],
    "outputs": {"water_occurrence": load_jrc_gsw_water_frac},
    "manifest_keys": {"water_occurrence": "jrc_gsw"},
}
```

### worldpop.py
```python
DOWNLOADER = {
    "name": "worldpop",
    "description": "WorldPop constrained population density",
    "requires_auth": ["none"],
    "outputs": {"population": load_worldpop_population},
    "manifest_keys": {"population": "worldpop"},
}
```

### glw.py
```python
DOWNLOADER = {
    "name": "glw",
    "description": "GLW4 livestock density",
    "requires_auth": ["none"],
    "outputs": {"livestock": load_glw_livestock},
    "manifest_keys": {"livestock": "glw"},
}
```

### ghsl.py
```python
DOWNLOADER = {
    "name": "ghsl",
    "description": "GHSL urban classification",
    "requires_auth": ["none"],
    "outputs": {"urban_class": load_ghsl_urban_class},
    "manifest_keys": {"urban_class": "ghsl"},
}
```

### wildlife.py
```python
DOWNLOADER = {
    "name": "wildlife",
    "description": "Wildlife host proxy",
    "requires_auth": ["none"],
    "outputs": {"wildlife_host_proxy": load_wildlife_host_proxy},
    "manifest_keys": {"wildlife_host_proxy": "wildlife"},
}
```

### buildings.py
```python
DOWNLOADER = {
    "name": "buildings",
    "description": "Overture Maps building fraction",
    "requires_auth": ["none"],
    "outputs": {"building_fraction": load_buildings_fraction},
    "manifest_keys": {"building_fraction": "buildings"},
}
```

---

## 4. Registry

`mal-core/src/mal_core/download/registry.py`:
```python
LOADER_MODULES = [
    "era5", "chirps", "dem", "jrc_gsw", "modis",
    "worldpop", "glw", "ghsl", "wildlife", "buildings",
]
```

All 10 loaders are registered. The registry discovers `DOWNLOADER` dicts via `importlib`.

---

## 5. Download Runner — REAL Behavior

`mal-core/src/mal_core/download/runner.py::run_download()`:

```python
def run_download(aoi, datasets=None, outputs=None, years=None, months=None, output_dir=None, **kwargs):
    aoi_obj = AOI.from_slug(aoi)
    registry = discover_downloaders()
    # ... filter by datasets/outputs ...
    
    for name, spec in selected.items():
        for output_name, func in spec.outputs.items():
            sig = inspect.signature(func)
            accepted = set(sig.parameters.keys())
            
            is_ts = _is_time_series(spec, output_name)  # checks if 'year' or 'years' in sig
            
            if is_ts and years:
                for year in years:
                    path = _standard_path(aoi, output_name, year, ext)
                    all_kwargs = {
                        "aoi": aoi_obj, "year": year, "years": [year],
                        "month": int(months[0]) if months else None,
                        "months": months, "output_path": str(path),
                    }
                    call_kwargs = {k: v for k, v in all_kwargs.items() if k in accepted and v is not None}
                    func(**call_kwargs)
                    update_dataset(aoi, output_name, year, path.name)
            else:
                path = _standard_path(aoi, output_name, None, ext)
                all_kwargs = {"aoi": aoi_obj, "output_path": str(path)}
                call_kwargs = {k: v for k, v in all_kwargs.items() if k in accepted and v is not None}
                func(**call_kwargs)
                update_dataset(aoi, output_name, None, path.name)
```

### Problems with the runner

1. **`output_path` is passed but ignored**: All loaders accept `output_path` in their signature
   but never actually save to that path. The runner thinks it's saving files to `data/<aoi>/`
   but nothing is written.

2. **Manifest keys are wrong**: The runner uses `output_name` (e.g., "temp_suitability", "elevation")
   as the manifest key, but the spec says manifest keys should be dataset names like "env", "wind",
   "habitat", "host_static".

3. **Time-series detection is fragile**: `_is_time_series` checks if 'year' or 'years' is in the
   function signature. For `load_era5_temp_suitability(aoi, year, month, ...)`, it finds 'year' →
   time-series. For `load_merit_dem(aoi, ...)`, no 'year' → static. This works but is fragile.

4. **jrc_gsw and worldpop get year=2024 even though they have year ranges**:
   - `load_jrc_gsw_water_frac(aoi, *, year=2021)` — max year is 2021
   - `load_worldpop_population(aoi, *, year=2019)` — max year is 2020
   - When runner passes `year=2024`, these loaders fail with "year must be in [X, Y]"

---

## 6. Ingest Modules

### 6.1 `mal-core/src/mal_core/ingest/env.py` — `build_env_tensor()`

Builds the 4-band env tensor (water_frac, rainfall, temp_suitability, ndvi) + habitat patches.

**Signature**:
```python
def build_env_tensor(aoi, year, month, output_dir, *, scale="regional", 
                     skip_era5=False, skip_modis=False, skip_jrc_gsw=False,
                     output_format="tif", name=None, twi_threshold=8.0) -> dict
```

**What it does**:
1. Loads water_frac via `load_jrc_gsw_water_frac(aoi, year=2021, month=month)`
2. Loads rainfall via `load_chirps_rainfall(aoi, year=year, month=month)`
3. Loads temp_suitability via `load_era5_temp_suitability(aoi, year=year, month=month)`
4. Loads ndvi via `load_modis_ndvi(aoi, year=year, month=month)`
5. Stacks into 4-band tensor, writes COG or NetCDF
6. Loads DEM via `load_merit_dem(aoi)`, computes TWI, detects habitat patches
7. Writes habitat GeoPackage
8. Registers in manifest as "env_tensor" and "habitat_patches"

**Critical bug**: `safe_load()` in `_shared.py` passes `year=year, month=month` to ALL loaders.
But `load_merit_dem(aoi, *, output_path=None, cache_dir=None)` does NOT accept year/month.
**Fix needed**: `safe_load` must inspect the loader's signature and only pass accepted kwargs.

### 6.2 `mal-core/src/mal_core/ingest/hosts.py` — `build_host_dataset()`

Builds static host density NetCDF.

**Signature**:
```python
def build_host_dataset(aoi, *, output_dir, worldpop_year=2019, cache_dir=None,
                       skip_buildings=False, skip_wildlife=False) -> dict
```

**What it does**:
1. Loads human population via `WorldPopLoader().load(aoi, year=worldpop_year)`
2. Loads livestock via `GLWLoader().load(aoi, species=...)` for 5 species
3. Loads urban class via `GHSLLoader().load(aoi)`
4. Loads building fraction via `BuildingsLoader().load(aoi)`
5. Loads wildlife proxy via `WildlifeLoader().load(aoi)`
6. Aggregates to grid, writes `host_static.nc` + `host_manifest.json`
7. Registers in manifest as "host_static" and "host_manifest"

**Issues**:
- Still uses class-style loaders, not function-style
- Output path is `output_dir / "host_static.nc"` — NOT spec-compliant naming (`<aoi>_host_static.nc`)

### 6.3 `mal-core/src/mal_core/ingest/mobility.py` — `build_mobility_dataset()`

Builds gravity-model OD matrices.

**Signature**:
```python
def build_mobility_dataset(hosts_path, *, output_dir, aoi_slug="ghana",
                           cell_size_km=1.0, beta_day=0.05, beta_night=0.5,
                           beta_livestock=0.1, max_distance_km=50.0) -> dict
```

**What it does**:
1. Loads `host_static.nc` data
2. Builds gravity OD for human day, human night, livestock
3. Writes 3 CSR files: `human_mobility_day.csr`, `human_mobility_night.csr`, `livestock_mobility_season.csr`
4. Registers in manifest

**Issues**:
- CSR filenames are NOT spec-compliant (`ghana_mobility_day.csr` not `human_mobility_day.csr`)
- Registers with wrong manifest keys (`mobility_human_mobility_day` instead of `mobility_day`)

---

## 7. ABM Wrapper

`mal-core/src/mal_core/abm/wrapper.py`:

**What it does**:
1. Reads manifest, validates completeness
2. Resolves paths: env, habitat, host_static, wind
3. Calls C++ binary with: `./mal_abm_fast run --env ... --habitat ... --hosts ...`
4. Returns output path + stdout/stderr

**C++ binary flags** (from `--help`):
```
--env TEXT REQUIRED          # Climate raster (.tif or .nc)
--habitat TEXT:FILE REQUIRED # Habitat patches (.gpkg)
--output TEXT REQUIRED       # Output state COG (.tif)
--hosts TEXT                 # Host density grid (.nc)
--human-mobility-day TEXT    # Human mobility OD (.csr)
--human-mobility-night TEXT  # Human mobility OD (.csr)
--livestock-mobility TEXT    # Livestock mobility OD (.csr)
--year INT REQUIRED
--month INT REQUIRED
--days INT [30]
--seed INT [1]
--n-rollouts INT [1]
```

**No `--wind-field` flag** — the binary doesn't support it. It's commented out in the wrapper.

---

## 8. Pipeline Runner

`mal-core/src/mal_core/pipeline/runner.py::run_stage()`:

For DOWNLOAD stage:
```python
if stage == Stage.DOWNLOAD:
    ys = extra.pop("years", "")
    years = [int(y.strip()) for y in ys.split(",") if y.strip()] if ys else None
    if not years and year is not None:
        years = [year]  # FIX: fallback to year param
    ms = extra.pop("months", "")
    months = [m.strip() for m in ms.split(",") if m.strip()] if ms else None
    if not months and month is not None:
        months = [str(month)]  # FIX: fallback to month param
    return run_download(aoi=aoi, datasets=datasets, outputs=out_list, 
                        years=years, months=months, output_dir=output_dir, **extra)
```

For INGEST stage:
```python
elif stage == Stage.INGEST:
    from mal_core.ingest import build_env_tensor
    return build_env_tensor(aoi=aoi, year=year, month=month, 
                            output_dir=output_dir / "ingest", **extra)
```

---

## 9. Dependencies

`mal-commonlib/pyproject.toml`:
```toml
dependencies = [
    "numpy>=2.5.0",
    "pandas>=3.0.3",
    "rasterio>=1.5.0",
    "rioxarray>=0.22.0",
    "scipy>=1.18.0",
    "pydantic>=2.7",
    "pyproj>=3.6",
    "shapely>=2.0",
    "geopandas>=0.14",
    "cdsapi>=0.7",
    "earthaccess>=0.12",
    "requests>=2.32",
    "h5py>=3.10",
    "pyhdf>=0.11",
    "planetary-computer>=1.0",
    "pystac-client>=0.8",
    "netcdf4>=1.7.4",
]
```

**Missing**: `pyarrow`, `pyogrio` (required by buildings loader).

---

## 10. AOI System

`mal-commonlib/src/mal_commonlib/aoi.py`:

```python
class AOI:
    slug: str
    name: str
    bbox: tuple[float, float, float, float]  # (west, south, east, north)
    crs: str
    resolution_m: int
    scale: Scale
    
    @classmethod
    def from_slug(cls, slug: str) -> "AOI":
        # Built-in registry: "ghana" → AOI.from_bbox(-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana", 1000)
```

---

## 11. Manifest System

`mal-core/src/mal_core/download/manifest.py`:

```python
def read_manifest(aoi: str) -> dict
def update_dataset(aoi: str, dataset_name: str, year: int|str|None, filename: str) -> Path
def validate_completeness(aoi: str) -> list[str]  # returns missing files
def get_dataset_files(aoi: str, dataset_name: str, year=None) -> list[Path]
```

**Current manifest** (from partial run, WRONG entries):
```json
{
  "datasets": {
    "temp_suitability": {"type": "time-series", "files": {"2024": "ghana_temp_suitability_2024.tif"}},
    "water_temp": {"type": "time-series", "files": {"2024": "ghana_water_temp_2024.tif"}},
    "wind_6hourly": {"type": "time-series", "files": {"2024": "ghana_wind_6hourly_2024.nc"}},
    "rainfall": {"type": "time-series", "files": {"2024": "ghana_rainfall_2024.tif"}},
    "elevation": {"type": "time-series", "files": {"2024": "ghana_elevation_2024.tif"}},
    ...
  }
}
```

**Problems**:
- Keys are output names ("temp_suitability"), not spec dataset names ("env")
- Files don't actually exist on disk (loaders don't save to output_path)
- Naming is wrong: should be `<aoi>_<product>_<year>.<ext>` not `<aoi>_<output_name>_<year>.<ext>`

---

## 12. Spec vs Reality

### download spec says:
- All loaders should follow unified signature: `load_<dataset>_<product>(aoi, *, year, month, output_path, cache_dir)`
- If `output_path` given: save to disk, return Path
- If `output_path=None`: return in-memory
- Runner calls each output with unified kwargs

### Reality:
- Function-style loaders accept `output_path` but IGNORE it (never save)
- Class-style loaders don't accept `output_path` at all
- Runner passes `output_path` thinking files are saved, but they aren't
- Manifest entries point to non-existent files

### data spec says:
- Spec dataset names: `env`, `wind`, `habitat`, `host_static`, `mobility_day`, etc.
- File naming: `<aoi>_<product>_<year>.<ext>` for time-series, `<aoi>_<product>.<ext>` for static

### Reality:
- Runner registers with output names ("elevation", "cattle"), not spec names
- Files don't exist on disk
- CSR files named `human_mobility_day.csr` not `ghana_mobility_day.csr`

---

## 13. All Identified Bugs

| # | Bug | File | Severity |
|---|-----|------|----------|
| 1 | `output_path` accepted but ignored by all function-style loaders | All 6 function-style loaders | **CRITICAL** |
| 2 | `safe_load()` passes year/month to `load_merit_dem` which doesn't accept them | `_shared.py` line 66-71 | **HIGH** |
| 3 | Runner registers manifest with wrong keys (output names vs spec names) | `runner.py` line 106, 116 | **HIGH** |
| 4 | Runner thinks files are saved to disk but they aren't | `runner.py` | **HIGH** |
| 5 | `jrc_gsw` fails when year=2024 passed (max 2021) | Runner passes year to all time-series loaders | **HIGH** |
| 6 | `worldpop` fails when year=2024 passed (max 2020) | Runner passes year to all time-series loaders | **HIGH** |
| 7 | `worldpop.py` has undefined `da` variable in `load_worldpop_population` | `worldpop.py` line ~195 | **HIGH** |
| 8 | `pyarrow`/`pyogrio` not in `pyproject.toml` | `mal-commonlib/pyproject.toml` | **MEDIUM** |
| 9 | `hosts.py` uses class-style loaders, not function-style | `hosts.py` lines 21-23, 67-68, 82-86 | **MEDIUM** |
| 10 | `mobility.py` CSR filenames not spec-compliant | `mobility.py` line 107-109 | **MEDIUM** |
| 11 | Ingest registers with wrong dataset names ("env_tensor" vs "env") | `env.py` line 424-433 | **MEDIUM** |
| 12 | No `--wind-field` flag in C++ binary | ABM wrapper comments it out | **LOW** (known) |

---

## 14. What the End-to-End Pipeline Should Do

```
malariasim run --aoi ghana --year 2024 --month 1 --stages download,ingest,build_hosts,build_mobility,abm
```

### Download stage:
1. For each registered loader, call the function with appropriate kwargs
2. Loader downloads data to its internal cache (`~/.cache/mal_commonlib/<dataset>/`)
3. Loader returns `xr.DataArray` (or `xr.Dataset` for wind)
4. **Runner saves the returned data to `data/<aoi>/<aoi>_<product>_<year>.<ext>`**
5. Runner registers in manifest with spec dataset name

### Ingest stage:
1. Load env channels from cache (chirps, era5, modis, jrc_gsw, dem)
2. Stack into 4-band tensor
3. Write to `data/<aoi>/<aoi>_env_<year>.nc` (or `.tif`)
4. Compute TWI, detect habitat patches
5. Write to `data/<aoi>/<aoi>_habitat.gpkg`
6. Register in manifest

### Build_hosts stage:
1. Load host data (worldpop, glw, ghsl, buildings, wildlife)
2. Aggregate to grid
3. Write to `data/<aoi>/<aoi>_host_static.nc`
4. Register in manifest

### Build_mobility stage:
1. Load `host_static.nc`
2. Build OD matrices
3. Write to `data/<aoi>/<aoi>_mobility_day.csr`, etc.
4. Register in manifest

### ABM stage:
1. Read manifest, validate completeness
2. Resolve paths from manifest
3. Call C++ binary with resolved paths

---

## 15. Key Design Decisions Already Made

1. **Model B chosen**: download = remote fetch, ingest = ABM-ready artifact production
2. **`worldcover` deprecated** — replaced by `jrc_gsw` in M2, archived to `_legacy/`
3. **`AOI.from_slug()` classmethod** added to `aoi.py` with Ghana registry
4. **C++ binary requires `run` subcommand**: `./mal_abm_fast run --env ... --habitat ...`
5. **C++ binary does NOT support `--wind-field`** — commented out in wrapper
6. **User HAS CDS auth and EARTHDATA_TOKEN** — era5/modis should work
7. **DFM volume** at `/Volumes/DFM/MalariaSentinel/` — old data backed up there
8. **Local `data/ghana/` deleted** for clean pipeline test — currently empty (only broken manifest)

---

## 16. What Needs to Happen (High-Level)

The planning model should produce a plan that:

1. **Makes loaders actually save to `output_path`** OR has the runner save the returned data
2. **Fixes `safe_load()` to inspect loader signatures** before passing year/month
3. **Uses spec dataset names in manifest** (not output names)
4. **Handles year ranges correctly** (jrc_gsw max 2021, worldpop max 2020)
5. **Fixes `worldpop.py` undefined `da`** variable
6. **Adds `pyarrow`/`pyogrio` to pyproject.toml**
7. **Makes `hosts.py` use function-style loaders**
8. **Makes CSR filenames spec-compliant**
9. **Cleans up the broken manifest**
10. **Validates end-to-end with Ghana 2024**

**The plan should be a proper restructuring, not hacks.** If loaders need to be modified to
actually use `output_path`, do that. If the runner needs to save returned data, do that.
But don't work around the problems — fix them at the source.

---

## 17. File Paths Reference

| File | Path |
|------|------|
| Era5 loader | `mal-commonlib/src/mal_commonlib/data/loaders/era5.py` |
| Chirps loader | `mal-commonlib/src/mal_commonlib/data/loaders/chirps.py` |
| DEM loader | `mal-commonlib/src/mal_commonlib/data/loaders/dem.py` |
| MODIS loader | `mal-commonlib/src/mal_commonlib/data/loaders/modis.py` |
| JRC GSW loader | `mal-commonlib/src/mal_commonlib/data/loaders/jrc_gsw.py` |
| WorldPop loader | `mal-commonlib/src/mal_commonlib/data/loaders/worldpop.py` |
| GLW loader | `mal-commonlib/src/mal_commonlib/data/loaders/glw.py` |
| GHSL loader | `mal-commonlib/src/mal_commonlib/data/loaders/ghsl.py` |
| Wildlife loader | `mal-commonlib/src/mal_commonlib/data/loaders/wildlife.py` |
| Buildings loader | `mal-commonlib/src/mal_commonlib/data/loaders/buildings.py` |
| WorldCover (legacy) | `mal-commonlib/src/mal_commonlib/data/loaders/_legacy/worldcover.py` |
| Download registry | `mal-core/src/mal_core/download/registry.py` |
| Download runner | `mal-core/src/mal_core/download/runner.py` |
| Manifest module | `mal-core/src/mal_core/download/manifest.py` |
| Pipeline runner | `mal-core/src/mal_core/pipeline/runner.py` |
| Pipeline stages | `mal-core/src/mal_core/pipeline/stages.py` |
| Ingest env | `mal-core/src/mal_core/ingest/env.py` |
| Ingest hosts | `mal-core/src/mal_core/ingest/hosts.py` |
| Ingest mobility | `mal-core/src/mal_core/ingest/mobility.py` |
| Ingest shared | `mal-core/src/mal_core/ingest/_shared.py` |
| ABM wrapper | `mal-core/src/mal_core/abm/wrapper.py` |
| AOI class | `mal-commonlib/src/mal_commonlib/aoi.py` |
| pyproject.toml | `mal-commonlib/pyproject.toml` |
| Download spec | `docs/specs/download/spec.md` |
| Data spec | `docs/specs/data/spec.md` |
