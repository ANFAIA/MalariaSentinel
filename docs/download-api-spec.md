# Download API Spec

Canonical reference for the MalariaSentinel data download plugin system.

## 1. Overview

Plugin-based download system at `mal-commonlib/src/mal_commonlib/data/loaders/`.

How it works:
- Each loader module exposes a `DOWNLOADER` dict.
- Registry (`mal-core/src/mal_core/download/registry.py`) discovers all `DOWNLOADER` dicts via `importlib`.
- Runner (`mal-core/src/mal_core/download/runner.py`) inspects each output callable's signature to detect time-series vs static, calls it with filtered kwargs, then saves the returned `xr.DataArray` / `xr.Dataset` via `save_product()` from `mal_core.download.writer`.
- Manifest (`mal-core/src/mal_core/download/manifest.py`) auto-updates `data/<aoi>/manifest.json` after each successful save.
- CLI command `malariasim download` invokes the runner.

> **Loaders do NOT accept `output_path`.** The runner is the single save point — loaders return data in memory, the runner persists to disk.

Registered loaders (all function-style, all registered):

| Loader | Auth | Outputs | Manifest Keys |
|--------|------|---------|---------------|
| `era5` | `cds` | `temp_suitability`, `water_temp`, `wind_6hourly` | `era5_temp`, `era5_water_temp`, `wind` |
| `chirps` | `none` | `rainfall`, `rainfall_daily` | `chirps_rainfall`, `chirps_rainfall_daily` |
| `dem` | `none` | `elevation` | `dem` |
| `jrc_gsw` | `none` | `water_occurrence` | `jrc_water` |
| `modis` | `earthdata` | `ndvi` | `modis_ndvi` |
| `worldpop` | `none` | `population` | `worldpop` |
| `glw` | `none` | `cattle`, `goats`, `sheep`, `pigs`, `chickens` | `glw_cattle`, `glw_goats`, `glw_sheep`, `glw_pigs`, `glw_chickens` |
| `ghsl` | `none` | `urban_class` | `ghsl_urban` |
| `wildlife` | `none` | `wildlife_host_proxy` | `wildlife_proxy` |
| `buildings` | `none` | `building_fraction` | `buildings` |

> **`worldcover` is DEPRECATED.** Use `jrc_gsw` for the `water_frac` channel. Archived to `mal-commonlib/.../loaders/_legacy/worldcover.py`.

## 2. Unified API — Load-or-Download

Every public function returns data in memory. The runner is the single save point.

### Canonical signature

```python
def load_<dataset>_<product>(
    aoi: AOI,                                  # REQUIRED, always first
    *,
    year: int | None = None,                   # REQUIRED for time-series
    month: int | None = None,                  # REQUIRED for some time-series
    cache_dir: pathlib.Path | None = None,     # default: ~/.cache/mal_commonlib/<dataset>
) -> xr.DataArray | xr.Dataset:
```

### Rules

- `aoi` is always the first positional arg.
- Time-invariant products (dem): `year=None, month=None` — both optional, ignored.
- Time-series products (chirps, era5 temp): `year` required, `month` required.
- Annual products (jrc_gsw, modis): `year` optional, `month` optional.
- The runner detects time-series by inspecting whether `year` is a required param (no default).
- Loaders **do NOT** accept `output_path` — the runner calls `save_product()` to persist.

### How the runner uses loaders

1. Runner inspects each output callable's signature via `inspect.signature`.
2. If `year` is required (no default) → time-series: loops over years, calls per year.
3. If `year` is optional or absent → static: calls once.
4. Passes only kwargs the loader accepts (filters by `accepted = set(sig.parameters.keys())`).
5. Saves the returned `xr.DataArray` or `xr.Dataset` via `save_product(data, path)`.
6. Registers in manifest via `update_dataset(aoi, manifest_key, year, path.name)`.

## 3. DOWNLOADER dict convention

Every loader module must export a `DOWNLOADER` dict. Example (era5):

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
4. **For each output**, inspect the callable's signature:
   - If `year` is required (no default) → **time-series**: loop over years, call per year.
   - If `year` is optional or absent → **static**: call once.
5. **Filter kwargs** to only those the loader accepts (`inspect.signature`).
6. **Call** the loader — it returns `xr.DataArray` or `xr.Dataset` in memory.
7. **Save** via `save_product(data, path)` from `mal_core.download.writer` (DataArray → GeoTIFF, Dataset → NetCDF).
8. **Register** in manifest via `update_dataset(aoi, manifest_key, year, path.name)`.

### Output path convention

```
data/<aoi>/<aoi>_<product>_<year>.<ext>   # time-series
data/<aoi>/<aoi>_<product>.<ext>          # static
```

Extension: `.tif` for raster DataArrays, `.nc` for Datasets (e.g., wind).

## 5. Manifest key mapping

| Loader | Output | Manifest Key |
|--------|--------|-------------|
| era5 | temp_suitability | era5_temp |
| era5 | water_temp | era5_water_temp |
| era5 | wind_6hourly | wind |
| chirps | rainfall | chirps_rainfall |
| chirps | rainfall_daily | chirps_rainfall_daily |
| dem | elevation | dem |
| modis | ndvi | modis_ndvi |
| jrc_gsw | water_occurrence | jrc_water |
| worldpop | population | worldpop |
| glw | cattle | glw_cattle |
| glw | goats | glw_goats |
| glw | sheep | glw_sheep |
| glw | pigs | glw_pigs |
| glw | chickens | glw_chickens |
| ghsl | urban_class | ghsl_urban |
| wildlife | wildlife_host_proxy | wildlife_proxy |
| buildings | building_fraction | buildings |

## 6. Adding a new dataset

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
    "era5", "chirps", "dem", "jrc_gsw", "modis",
    "worldpop", "glw", "ghsl", "wildlife", "buildings",
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

The refactoring is complete. All loaders now follow the canonical signature (function-style, no `output_path`, `aoi` as first arg).

### What changed

| Before | After |
|--------|-------|
| `download_era5_wind_6hourly(years, output_path)` | `load_era5_wind_6hourly(aoi, *, years)` — runner saves |
| `class WorldPopLoader` etc. | `load_worldpop_population()` (function-style) |
| Loaders accepted `output_path` | Loaders return data; runner calls `save_product()` |
| `worldcover` loader | **Deprecated** — use `jrc_gsw` |
| Class-style loaders (ghsl, glw, wildlife, buildings, worldpop) | Function-style, registered in downloader registry |

### Backward compatibility

- `download_era5_wind_*` callers must switch to `load_era5_wind_6hourly`.
- Runner (`run_download`) uses `inspect.signature` to adapt kwargs — no changes needed at call sites.

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
ds = load_era5_wind_6hourly(
    aoi,
    years=[2024, 2025],
    months=MIGRATION_SEASON_MONTHS[2024] + MIGRATION_SEASON_MONTHS[2025],
)
# Runner saves to data/ghana/ghana_wind_2024.nc, etc.
```
