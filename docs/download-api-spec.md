# Download API Spec

Canonical reference for the MalariaSentinel data download plugin system.

## 1. Overview

Plugin-based download system at `mal-commonlib/src/mal_commonlib/data/loaders/`.

> **Note (2026-07-29)**: The `worldcover` loader is deprecated (replaced by `jrc_gsw` in M2). The class-style loaders (`ghsl`, `glw`, `wildlife`, `buildings`, `worldpop`) are being refactored to function-style and will be registered in the downloader registry in Phase 2 of the unify-download-ingest-build initiative.

How it works:
- Each loader module exposes a `DOWNLOADER` dict.
- Registry (`mal-core/src/mal_core/download/registry.py`) discovers all `DOWNLOADER` dicts via `importlib`.
- Runner (`mal-core/src/mal_core/download/runner.py`) calls each output callable with unified kwargs.
- Manifest (`mal-core/src/mal_core/download/manifest.py`) auto-updates `data/<aoi>/manifest.json` after each successful download.
- CLI command `malariasim download` invokes the runner.

Registered loaders:

| Loader | Auth | Outputs | Status |
|--------|------|---------|--------|
| `era5` | `cds` | `temp_suitability`, `water_temp`, `wind_6hourly` | Active |
| `chirps` | `none` | `rainfall`, `rainfall_daily` | Active |
| `dem` | `none` | `elevation` | Active |
| `jrc_gsw` | `none` | `water_occurrence` | Active |
| `modis` | `earthdata` | `ndvi` | Active |
| `worldcover` | `none` | `water_frac` | **DEPRECATED** (replaced by `jrc_gsw` in M2) |
| `ghsl` | `none` | `urban_class` | Pending Phase 2 |
| `glw` | `none` | `livestock` | Pending Phase 2 |
| `wildlife` | `none` | `wildlife_host_proxy` | Pending Phase 2 |
| `buildings` | `none` | `building_fraction` | Pending Phase 2 |
| `worldpop` | `none` | `population` | Pending Phase 2 |

## 2. Unified API — Load-or-Download

Every public function follows this pattern:

```python
def load_<dataset>_<product>(
    aoi: AOI | str,                              # REQUIRED, always first
    *,
    year: int | list[int] | None = None,         # singular for load
    month: int | list[int] | None = None,        # singular for load
    years: int | list[int] | None = None,        # plural for download
    months: int | str | list[int | str] | None = None,  # plural for download
    output_path: str | Path | None = None,       # None = in-memory
    cache_dir: Path | None = None,               # default: ~/.cache/mal_commonlib/<dataset>
) -> xr.DataArray | xr.Dataset | Path:
```

### Rules

- `aoi` is always the first positional arg.
- Time-invariant products (dem): `year=None, month=None` — both optional, ignored.
- Time-series products (chirps, era5 temp): `year` required, `month` required.
- Annual products (jrc_gsw, worldcover): `year` optional, `month` optional.
- Download-heavy products (era5 wind): `years` required (multi-year), `month`/`months` optional.
- If `output_path` is given: save to disk, return `Path`.
- If `output_path` is `None`: return in-memory (`xr.DataArray` or `xr.Dataset`).

### Internal implementation

Each loader has two private functions:

- `_download_<product>(...)` — fetch from remote, save to cache.
- `_load_from_cache(...)` — read cached file, reproject to AOI grid.

Public function decides:
```
if cached → _load_from_cache
else → _download → cache → _load_from_cache
```

### Current vs target signatures

| Loader | Current | Target |
|--------|---------|--------|
| `load_chirps_rainfall` | `(aoi, year, month)` | `(aoi, *, year, month)` |
| `load_merit_dem` | `(aoi)` | `(aoi)` — already correct |
| `load_era5_temp_suitability` | `(aoi, year, month)` | `(aoi, *, year, month)` |
| `download_era5_wind_6hourly` | `(years, output_path)` | `(aoi, *, years, output_path)` |
| `load_jrc_gsw_water_frac` | `(aoi, year=None, month=None)` | `(aoi, *, year=None, month=None)` — already correct |

## 3. DOWNLOADER dict convention

Every loader module must export a `DOWNLOADER` dict:

```python
DOWNLOADER = {
    "name": "era5",                           # unique string
    "description": "ERA5 reanalysis...",      # human-readable
    "requires_auth": ["cds"],                 # auth mechanisms
    "outputs": {
        "temp_suitability": load_era5_temp_suitability,  # callable
    },
    "manifest_keys": {
        "temp_suitability": "era5_temp",      # key in manifest.json
    },
}
```

### Auth values

| Value | Meaning |
|-------|---------|
| `"cds"` | Copernicus CDS API (`~/.cdsapirc` or `CDSAPI_URL`/`CDSAPI_KEY` env vars) |
| `"earthdata"` | NASA Earthdata (`EARTHDATA_TOKEN` env var) |
| `"planetary_computer"` | Microsoft Planetary Computer (no auth needed, signed URLs) |
| `"none"` | Public data, no auth required |

### `outputs` dict

Keys are output names (strings). Values are callables — the public `load_<dataset>_<product>` functions. The runner calls them with unified kwargs.

### `manifest_keys` dict

Maps output names to keys in `data/<aoi>/manifest.json`. Used by the runner to update the manifest after each successful download.

## 4. Runner behavior

`run_download()` in `mal-core/src/mal_core/download/runner.py`:

1. **Discover** all `DOWNLOADER` dicts via `importlib` (registry).
2. **Filter** by `--datasets` and `--outputs` CLI flags.
3. **Check auth** for each selected downloader. Skip if auth missing.
4. **Call** each output callable with unified kwargs (`aoi`, `years`, `months`, `output_path`).
5. **Update manifest** after each successful download.

### Runner signature

```python
def run_download(
    aoi: str,
    datasets: list[str] | None = None,
    years: list[int] | None = None,
    months: list[str] | None = None,
    output_dir: str | Path | None = None,
    **kwargs,
) -> dict[str, Any]:
```

### Auth check logic

```python
def _check_auth(spec: DownloaderSpec) -> bool:
    for auth in spec.requires_auth:
        if auth == "cds":
            # check ~/.cdsapirc exists
        elif auth == "earthdata":
            # check EARTHDATA_TOKEN env var
    return True
```

### Output path convention

```
data/<aoi>/<aoi>_<output_name>.<ext>
```

Extension: `.nc` for download-heavy products, `.tif` for raster products.

### Manifest update

After each successful download, runner calls:
```python
update_manifest(aoi, manifest_key, filename)
```

Where `manifest_key` comes from `DOWNLOADER["manifest_keys"][output_name]`.

## 5. Adding a new dataset

Step-by-step guide.

### 1. Create loader module

File: `mal-commonlib/src/mal_commonlib/data/loaders/<dataset>.py`

```python
def load_<dataset>_<product>(
    aoi: AOI,
    *,
    year: int | None = None,
    month: int | None = None,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load <product> for the AOI.

    Args:
        aoi: the AOI.
        year, month: time parameters (optional for annual products).
        cache_dir: optional local cache.

    Returns:
        xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
        NoData: -9999.0.
    """
    cache = _ensure_cache_dir(cache_dir)

    if _is_cached(cache, aoi, year, month):
        return _load_from_cache(cache, aoi, year, month)

    _download_<dataset>_<product>(aoi, year, month, cache)
    return _load_from_cache(cache, aoi, year, month)
```

### 2. Implement internal functions

```python
def _download_<dataset>_<product>(aoi, year, month, cache):
    """Fetch from remote, save to cache."""
    # Download logic here
    pass

def _load_from_cache(cache, aoi, year, month):
    """Read cached file, reproject to AOI grid."""
    # Read + reproject logic here
    pass
```

### 3. Add DOWNLOADER dict

```python
DOWNLOADER = {
    "name": "<dataset>",
    "description": "<human-readable description>",
    "requires_auth": ["<auth_mechanism>"],
    "outputs": {
        "<product>": load_<dataset>_<product>,
    },
    "manifest_keys": {
        "<product>": "<manifest_key>",
    },
}
```

### 4. Register in registry

Add `"<dataset>"` to `LOADER_MODULES` in `mal-core/src/mal_core/download/registry.py`:

```python
LOADER_MODULES = [
    "era5", "chirps", "dem", "jrc_gsw", "modis", "worldcover",
    "ghsl", "glw", "wildlife", "buildings",
    "<dataset>",  # new
]
```

### 5. Add manifest key mapping

In `DOWNLOADER["manifest_keys"]`, map each output to a unique key in `manifest.json`.

### 6. Write tests

Create `mal-commonlib/tests/test_load_<dataset>.py`. Test:
- Auth check (if applicable)
- Cache hit/miss
- Reprojection to AOI grid
- NoData handling

### 7. Run the download

```bash
malariasim download --aoi <aoi> --datasets <dataset> --years <years>
```

## 6. Migration notes

What's changing.

### Current state (inconsistent signatures)

```python
load_chirps_rainfall(aoi, year, month)          # required all
load_merit_dem(aoi)                              # time-invariant
load_era5_temp_suitability(aoi, year, month)     # required all
download_era5_wind_6hourly(years, output_path)   # NO aoi, plural
load_jrc_gsw_water_frac(aoi, year=None, month=None)  # optional time
```

### Migration plan

| Change | What | Why |
|--------|------|-----|
| `load_*` functions | Keep signatures, add `aoi` as first arg where missing | Unified API |
| `download_era5_wind_*` | Rename to `_download_era5_wind` (private), add public `load_era5_wind_6hourly` | Public = load-or-download |
| `download_era5_wind_migration_season` | Delete | Use `months=MIGRATION_SEASON_MONTHS[year]` instead |
| `class WorldPopLoader` etc. | Refactored to `load_worldpop_population()` (function-style) | Spec §2 compliance |
| All loaders | Internalize download logic into `_download_*` private functions | Clean public surface |

### Detailed changes

**`download_era5_wind_6hourly(years, output_path)` → `load_era5_wind_6hourly(aoi, *, years, output_path)`**

- Add `aoi` as first arg (currently missing).
- Rename from `download_*` to `load_*` (public = load-or-download).
- Move current implementation to `_download_era5_wind(aoi, years, months, cache)`.
- Add `_load_from_cache(cache, aoi, years)` to read cached NetCDF.
- Public function: if cached → load, else → download → cache → load.

**`download_era5_wind_migration_season(years, output_path)` → delete**

- Convenience wrapper. Replace with:
  ```python
  load_era5_wind_6hourly(aoi, years=years, months=MIGRATION_SEASON_MONTHS[year])
  ```
- Or pass `months` as a CLI arg: `--months 07,08,09,10,12`.

**All `load_*` functions: internalize download logic**

- Extract download logic into `_download_<product>()`.
- Extract cache-read logic into `_load_from_cache()`.
- Public function: cache check → download if needed → load.

### Backward compatibility

- Old call sites (`load_chirps_rainfall(aoi, year, month)`) continue to work.
- `download_era5_wind_*` callers must switch to `load_era5_wind_6hourly`.
- Runner (`run_download`) uses `inspect.signature` to adapt kwargs — no changes needed.

## 7. Examples

### Download wind for 2024-2025

```bash
malariasim download --aoi ghana --datasets era5 --outputs wind_6hourly --years 2024 2025
```

### Download all era5 products

```bash
malariasim download --aoi ghana --datasets era5 --years 2024
```

### Download everything for an AOI

```bash
malariasim download --aoi ghana --all
```

### Full pipeline

```bash
malariasim run --stages download,ingest,abm,scoring,training,prediction --aoi ghana
```

### Programmatic usage

```python
from mal_commonlib.data.loaders.era5 import load_era5_temp_suitability
from mal_commonlib.aoi import AOI

aoi = AOI.from_slug("ghana")
da = load_era5_temp_suitability(aoi, year=2024, month=7)
print(da.shape)  # (H, W)
print(da.attrs["nodata"])  # -9999.0
```

### Download wind for migration season only

```python
from mal_commonlib.data.loaders.era5 import load_era5_wind_6hourly, MIGRATION_SEASON_MONTHS

aoi = AOI.from_slug("ghana")
path = load_era5_wind_6hourly(
    aoi,
    years=[2024, 2025],
    months=MIGRATION_SEASON_MONTHS[2024] + MIGRATION_SEASON_MONTHS[2025],
)
```
