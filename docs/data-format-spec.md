# Data Format Spec

Canonical reference for MalariaSentinel data file naming, manifest schema, and loader/downloader/ABM contracts.

Companion: [`download-api-spec.md`](download-api-spec.md) covers the plugin system, `DOWNLOADER` dicts, and runner behavior. This file covers the data format layer — what files look like on disk, how the manifest tracks them, and how loaders/ABM consume them.

## 1. Overview

The manifest (`data/<aoi>/manifest.json`) is the **single source of truth** for an AOI's data inventory.

- **Downloaders** register files in the manifest after each successful download.
- **Loaders** resolve paths from the manifest before loading.
- **ABM** validates completeness via the manifest before starting a simulation.

This decouples file naming from code — loaders and the ABM never hardcode paths. The manifest owns the mapping.

## 2. File naming convention

```
data/<aoi>/
  <aoi>_<product>_<year>.<ext>     # time-series, per-year
  <aoi>_<product>.<ext>            # static/time-invariant
```

### Current files (data/ghana/, post-migration)

| File | Dataset | Type |
|---|---|---|
| `ghana_regional_2024_2025_env.nc` | env | time-series (2024+2025 combined) |
| `ghana_wind_2024.nc` | wind | time-series |
| `ghana_wind_2025.nc` | wind | time-series |
| `ghana_habitat.gpkg` | habitat | static |
| `ghana_host_static.nc` | host_static | static |
| `ghana_host_manifest.json` | host_manifest | static |
| `ghana_mobility_day.csr` | mobility_day | static |
| `ghana_mobility_night.csr` | mobility_night | static |
| `ghana_livestock_mobility.csr` | livestock_mobility | static |

Legacy names (pre-migration):

| Old name | New name |
|---|---|
| `wind_era5_6hourly_2024.nc` | `ghana_wind_2024.nc` |
| `wind_era5_6hourly_2025.nc` | `ghana_wind_2025.nc` |
| `ghana_regional_2024_06_habitat_patches.gpkg` | `ghana_habitat.gpkg` |
| `host_static.nc` | `ghana_host_static.nc` |
| `human_mobility_day.csr` | `ghana_mobility_day.csr` |
| `human_mobility_night.csr` | `ghana_mobility_night.csr` |
| `livestock_mobility_season.csr` | `ghana_livestock_mobility.csr` |

Migration script: `scripts/migrate_data_format.py` (idempotent).

## 3. Dataset types

| Dataset | Type | Format | Frequency | File pattern | Variables | `required_for_abm` |
|---|---|---|---|---|---|---|
| `env` | time-series | NetCDF4 | daily | `<aoi>_env_<year>.nc` | rainfall, water_temp_c, water_frac, ndvi | yes |
| `wind` | time-series | NetCDF4 | 6-hourly | `<aoi>_wind_<year>.nc` | u100, v100 | no |
| `habitat` | static | GeoPackage | — | `<aoi>_habitat.gpkg` | geometry (row, col, K, TWI) | yes |
| `host_static` | static | NetCDF4 | — | `<aoi>_host_static.nc` | host density | yes |
| `host_manifest` | static | JSON | — | `<aoi>_host_manifest.json` | host metadata | yes |
| `mobility_day` | static | CSR | — | `<aoi>_mobility_day.csr` | OD matrix (daytime) | no |
| `mobility_night` | static | CSR | — | `<aoi>_mobility_night.csr` | OD matrix (nighttime) | no |
| `livestock_mobility` | static | CSR | — | `<aoi>_livestock_mobility.csr` | OD matrix (livestock) | no |

> **Deprecated**: The `worldcover` dataset is deprecated; use `jrc_gsw` for the `water_frac` channel.

### Type semantics

- **time-series**: one file per year (or multi-year). ABM loads by year. Manifest tracks per-year file mapping.
- **static**: one file per AOI. No year dimension. Manifest tracks a single file entry.

## 4. Manifest schema v2

Location: `data/<aoi>/manifest.json`

```json
{
  "aoi": "ghana",
  "name": "Ghana NMCP AOI",
  "grid": {
    "bbox": [-3.5, 4.5, 1.5, 11.5],
    "crs": "EPSG:4326",
    "resolution_m": 1000,
    "height": 779,
    "width": 551
  },
  "datasets": {
    "env": {
      "type": "time-series",
      "format": "nc",
      "temporal": { "freq": "daily" },
      "files": {
        "2024": "ghana_regional_2024_2025_env.nc",
        "2025": "ghana_regional_2024_2025_env.nc"
      },
      "variables": ["rainfall", "water_temp_c", "water_frac", "ndvi"],
      "required_for_abm": true
    },
    "wind": {
      "type": "time-series",
      "format": "nc",
      "temporal": { "freq": "6hourly" },
      "files": {
        "2024": "ghana_wind_2024.nc",
        "2025": "ghana_wind_2025.nc"
      },
      "variables": ["u100", "v100"],
      "required_for_abm": false
    },
    "habitat": {
      "type": "static",
      "format": "gpkg",
      "files": { "habitat": "ghana_habitat.gpkg" },
      "required_for_abm": true
    },
    "host_static": {
      "type": "static",
      "format": "nc",
      "files": { "host_static": "ghana_host_static.nc" },
      "required_for_abm": true
    },
    "mobility_day": {
      "type": "static",
      "format": "csr",
      "files": { "mobility_day": "ghana_mobility_day.csr" },
      "required_for_abm": false
    }
  },
  "expected_files": [
    "ghana_habitat.gpkg",
    "ghana_host_static.nc",
    "ghana_host_manifest.json",
    "ghana_livestock_mobility.csr",
    "ghana_mobility_day.csr",
    "ghana_mobility_night.csr",
    "ghana_regional_2024_2025_env.nc",
    "ghana_wind_2024.nc",
    "ghana_wind_2025.nc"
  ]
}
```

### Schema fields

| Field | Required | Description |
|---|---|---|
| `aoi` | yes | AOI slug (matches directory name under `data/`) |
| `name` | no | Human-readable AOI name |
| `grid` | no | Spatial grid definition (bbox, CRS, resolution, dimensions) |
| `datasets` | yes | Map of dataset name → dataset entry |
| `expected_files` | yes | Flat list of all expected filenames. Used by `validate_completeness()`. |

### Dataset entry fields

| Field | Required | Description |
|---|---|---|
| `type` | yes | `"time-series"` or `"static"` |
| `format` | yes | File extension (`nc`, `gpkg`, `csr`, `json`, `tif`) |
| `temporal` | no | `{ "freq": "daily" }` or `{ "freq": "6hourly" }` (time-series only) |
| `files` | yes | Map of year→filename (time-series) or key→filename (static) |
| `variables` | no | List of variable names in the file |
| `required_for_abm` | yes | Whether the ABM refuses to start without this dataset |

### v1 → v2 migration

The manifest module (`mal-core/src/mal_core/download/manifest.py`) auto-migrates v1 (flat `files` dict) to v2 (datasets block) in memory on read. Writes always produce v2. The migration script `scripts/migrate_data_format.py` does the on-disk migration including file renames.

## 5. Manifest API

Module: `mal-core/src/mal_core/download/manifest.py`

### `read_manifest(aoi: str) -> dict`

Read manifest for an AOI. Auto-migrates v1→v2 in memory. Returns empty manifest if file doesn't exist.

### `update_dataset(aoi, dataset_name, year, filename) -> Path`

Update a specific dataset entry. Creates the dataset block if it doesn't exist. Rebuilds `expected_files` from all datasets. Writes v2 format.

- `year`: `int | str | None`. For time-series, the year key. For static, `None` (uses dataset_name as key).

### `validate_completeness(aoi: str) -> list[str]`

Returns list of missing expected files. Empty list = complete. Checks each entry in `expected_files` against `data/<aoi>/`.

### `get_dataset_files(aoi, dataset_name, year=None) -> list[Path]`

Get resolved file paths for a dataset. If `year` is given, returns single file for that year. If `None`, returns all files for the dataset.

### `list_files(aoi) -> dict[str, str]`

Flat filename dict (v1 compatibility shim). Aggregates all `files` entries across datasets.

## 6. Loader contract

Every public loader function returns data in memory. The runner is the single save point.

### Signature

```python
def load_<dataset>_<product>(
    aoi: AOI,
    *,
    year: int | None = None,        # REQUIRED for time-series
    month: int | None = None,       # REQUIRED for some time-series
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray | xr.Dataset:
```

### Behavior

1. Resolve path from manifest (`get_dataset_files`).
2. If file exists on disk → load and return.
3. If missing → download → save to standard path → register in manifest (`update_dataset`) → load and return.
4. **No `output_path` param** — loaders return data; the runner calls `save_product()` to persist.

### Loader ↔ manifest interaction

```python
from mal_core.download.manifest import get_dataset_files, update_dataset

# Resolve
paths = get_dataset_files(aoi, "wind", year=2024)
if paths and paths[0].exists():
    return xr.load_dataarray(paths[0])

# Download, save, register
path = _download(aoi, year)
update_dataset(aoi, "wind", year, path.name)
return xr.load_dataarray(path)
```

## 7. Downloader contract

The runner (`mal-core/src/mal_core/download/runner.py`) orchestrates downloads.

### Standard path function

```python
def _standard_path(aoi: str, product: str, year: int | None, ext: str) -> Path:
    data_dir = _REPO_ROOT / "data" / aoi
    if year:
        return data_dir / f"{aoi}_{product}_{year}.{ext}"
    return data_dir / f"{aoi}_{product}.{ext}"
```

### Runner flow

1. Discover all `DOWNLOADER` dicts via registry.
2. Filter by `--datasets` and `--outputs` CLI flags.
3. Check auth for each selected downloader. Skip if missing.
4. For each output:
   - If time-series + years provided: loop over years, call function per year.
   - If static or no year: call once.
5. After each successful call: `update_dataset(aoi, output_name, year, path.name)`.

### Runner signature

```python
def run_download(
    aoi: str,
    datasets: list[str] | None = None,
    outputs: list[str] | None = None,
    years: list[int] | None = None,
    months: list[str] | None = None,
    output_dir: str | Path | None = None,
    **kwargs,
) -> dict[str, Any]:
```

Returns `{ "<downloader_name>": {"status": "ok"|"skipped"|"error", ...} }`.

## 8. ABM validation

The ABM wrapper (`mal-core/src/mal_core/abm/wrapper.py`) validates data completeness before starting.

### Manifest-driven ABM

```python
def run_abm_from_manifest(aoi, year, month, days, seed, ...):
    manifest = read_manifest(aoi)
    missing = validate_completeness(aoi)
    if missing:
        raise FileNotFoundError(f"Missing data files: {missing}")

    # Resolve paths from manifest
    env_path = get_dataset_files(aoi, "env", year)[0]
    wind_path = get_dataset_files(aoi, "wind", year)[0]
    habitat_path = get_dataset_files(aoi, "habitat")[0]
    # ... etc

    # Call C++ binary with resolved paths
    _run_cpp_binary(env_path, wind_path, habitat_path, ...)
```

### Pipeline dispatch

The pipeline runner dispatches the ABM stage in manifest mode:

```bash
malariasim run --stages abm --aoi ghana --year 2024
```

This reads the manifest, validates completeness, resolves paths, and invokes the C++ binary.

## 9. How to add a new dataset

### 1. Create or update loader module

File: `mal-commonlib/src/mal_commonlib/data/loaders/<dataset>.py`

```python
DOWNLOADER = {
    "name": "<dataset>",
    "description": "<human-readable>",
    "requires_auth": ["none"],
    "outputs": {
        "<product>": load_<dataset>_<product>,
    },
    "manifest_keys": {
        "<product>": "<dataset>",
    },
}

def load_<dataset>_<product>(aoi, *, year=None, month=None, cache_dir=None):
    # Load-or-download: return xr.DataArray or xr.Dataset
    ...
```

### 2. Register in registry

Add `"<dataset>"` to `LOADER_MODULES` in `mal-core/src/mal_core/download/registry.py`.

### 3. Define file pattern

Use standard naming: `<aoi>_<product>_<year>.<ext>` (time-series) or `<aoi>_<product>.<ext>` (static).

### 4. Run download

```bash
malariasim download --aoi <aoi> --datasets <dataset> --years <years>
```

Runner auto-registers files in manifest.

### 5. Mark `required_for_abm`

If the ABM needs this dataset, update the manifest entry:

```json
"<dataset>": {
    "type": "time-series",
    "format": "<ext>",
    "files": { "<year>": "<aoi>_<product>_<year>.<ext>" },
    "required_for_abm": true
}
```

### 6. Update ABM wrapper

If `required_for_abm=true`, add path resolution in `run_abm_from_manifest()`.

### 7. Write tests

- Test `load_or_download` with cache hit/miss.
- Test `update_dataset` writes correct manifest structure.
- Test `validate_completeness` with missing files.
- Test ABM rejects start when required files missing.
