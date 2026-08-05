# data Spec

> Owns the **on-disk data layout**: file naming, dataset types,
> manifest schema, and the directory layout under `data/<aoi>/`. The
> single source of truth for "where is the env file for AOI `ghana`,
> year 2024?". Every other layer (download, ingest, abm, training,
> prediction) reads and writes through this layout.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: download
    direction: bidirectional
    reason: download writes files under data/<aoi>/ using the canonical naming; download also updates the manifest
    severity: breaking
  - target: ingest
    direction: bidirectional
    reason: ingest reads from manifest paths and writes under output_dir; ingester helpers call register_dataset
    severity: breaking
  - target: abm
    direction: upstream
    reason: abm wrapper resolves env/host/wind/habitat paths via manifest; validation reads expected_files
    severity: breaking
  - target: training
    direction: downstream
    reason: training reads rollout state files and env tensors; env channel order and naming pinned here
    severity: breaking
  - target: prediction
    direction: downstream
    reason: prediction loads env stack + ABM state by sidecar/manifest; contract_version pinned here
    severity: breaking
  - target: commonlib
    direction: bidirectional
    reason: data root path computed in commonlib.config; loaders live in commonlib.data.loaders
    severity: non-breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: [adr-spec-design-2026-07-30]
  patterns: []
  pitfalls: []
  tools: []
```

## Metadata

| Field | Value |
|---|---|
| Component | `mal-core/src/mal_core/download/manifest.py` + `data/<aoi>/` |
| Version | `v3.1` (manifest schema); `v2.0` (file naming); `v2.0` (env NetCDF) |
| Status | `stable` (naming); `stable` (manifest v3.1 schema) |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-08-05` |

## 1. Objective

The data spec exists to **decouple file naming from code**. Loaders,
ingest, the ABM wrapper, training, and prediction never hardcode a
path — they ask the manifest. The manifest is the single source of
truth; everything else is a consumer.

Without this spec the system would have a hardcoded `data/ghana/...`
string in 12 places and any rename would silently break the pipeline.

## 2. In scope

- File naming convention for `data/<aoi>/`.
- Manifest schema (v3.1) at `data/<aoi>/manifest.json`.
- Dataset type semantics (`time-series` vs `static`).
- Manifest API (`read_manifest`, `update_dataset`, `validate_completeness`, `get_dataset_files`, `list_files`).
- Env NetCDF format (CF-1.8 daily) and env COG/TIF format.
- Loader contract (signatures, `DOWNLOADER` dict, return type).
- ABM manifest validation flow.

## 3. Out of scope

- DOWNLOADER dict internals → `docs/specs/download/spec.md`.
- ABM env tensor **consumption** semantics → `docs/specs/abm/spec.md` (channel meanings, K_max).
- How ingest builds each dataset → `docs/specs/ingest/spec.md`.
- AOI schema itself → `docs/specs/commonlib/spec.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `read_manifest(aoi)` | `mal_core.download.manifest` | Returns the full manifest dict. Auto-migrates v1 → v2 in memory. Empty skeleton if file missing. |
| `update_dataset(aoi, dataset_name, year, filename, *, type, required_for_abm, variables, format, period)` | `mal_core.download.manifest` | Updates one dataset entry, rebuilds `expected_files`, writes v3.1. All kwargs are written to disk. |
| `update_manifest(aoi, key, filename)` | `mal_core.download.manifest` | Legacy compat wrapper — delegates to `update_dataset`. |
| `validate_completeness(aoi, *, years=None)` | `mal_core.download.manifest` | Returns `list[str]` of missing filenames (empty = complete). When `years` is provided, period-based NC entries are checked for year coverage. |
| `get_dataset_files(aoi, dataset_name, year=None)` | `mal_core.download.manifest` | Returns resolved `list[Path]` (empty if not found). |
| `list_files(aoi)` | `mal_core.download.manifest` | Flat dict (v1 compat). |
| `register_dataset(...)` | `mal_core.ingest._shared` | Thin wrapper around `update_dataset` used by ingest builders. |

## 5. Invariants

### §5.1 File naming (data/)

- **INV-1.** Time-series file: `data/<aoi>/<aoi>_<product>_<year>.<ext>` — one file per year.
- **INV-2.** Static file: `data/<aoi>/<aoi>_<product>.<ext>` — one file per AOI.
- **INV-3.** `<aoi>` matches `[a-z0-9]+(-[a-z0-9]+)*` (delegated to `AOI.slug` validator).
- **INV-4.** Manifest entries live under `data/<aoi>/manifest.json`.

### §5.2 Manifest schema v3.1

- **INV-5.** Top-level keys: `aoi` (required), `name` (optional), `grid` (optional), `datasets` (required), `expected_files` (required).
- **INV-6.** Each dataset entry: `type` ∈ `{"time-series","static"}`, `format` ∈ `{nc,gpkg,csr,json,tif}`, `files` map (`year → filename` for time-series, `key → filename` for static), `required_for_abm` (bool, defaults to false), `variables` (list, optional), `period` (dict, optional — see §6.2).
- **INV-7.** `expected_files` is the flat sorted union of all `files` values. `validate_completeness` checks each against `data/<aoi>/`.
- **INV-8.** Reader auto-migrates v1 (flat `files` dict) to v2 in memory. **Writes always produce v3.1.** Migration script: `scripts/migrate_data_format.py`.
- **INV-9.** A dataset missing from the manifest is **not** available to consumers (the ABM raises `FileNotFoundError`).

### §5.3 Env tensor formats

- **INV-10.** COG/TIF env file (ingest default `output_format="tif"`):
  - Bands in order: `water_frac, rainfall, temp_suitability, ndvi`.
  - `dtype = float32`, NoData `-9999.0`, tile size `128×128`, deflate.
  - Sidecar carries `band_names`, `nodata`, `shape`, `contract_version: "1.0"`, `generator_version`, `crs`, `transform`.
- **INV-11.** Daily NetCDF env file (ingest `output_format="nc"`):
  - CF-1.8 conventions, dims `(time, y, x)`, vars `rainfall, water_temp_c, water_frac, ndvi`.
  - `time` axis covers the full month (e.g. 28–31 days).
  - `contract_version: "2.0"` (note: differs from the COG file — see §7).
- **INV-12.** NetCDF `_FillValue` and COG `nodata` are both `-9999.0`.

### §5.4 Loader contract

- **INV-13.** Every loader function returns `xr.DataArray | xr.Dataset` **in memory**. No `output_path` param.
- **INV-14.** Canonical signature: `load_<dataset>_<product>(aoi: AOI, *, years: Sequence[int], months: Sequence[int] | None = None, cache_dir: Path | None = None)`. Some loaders (e.g. `jrc_gsw`) use `year: int` instead of `years: Sequence[int]` for static annual products.
- **INV-15.** Load-or-download semantics: try manifest first, return cached; if missing, download, save via runner, register, return.

## 6. Data contracts

### §6.1 Manifest schema (full example — v3.1)

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
      "variables": ["water_frac", "rainfall", "water_temp_c", "ndvi"],
      "required_for_abm": true,
      "period": { "start": "2024-01-01", "end": "2025-12-31" }
    },
    "habitat": {
      "type": "static",
      "format": "gpkg",
      "files": { "habitat": "ghana_habitat.gpkg" },
      "required_for_abm": true
    }
  },
  "expected_files": ["ghana_habitat.gpkg", "ghana_regional_2024_2025_env.nc"]
}
```

### §6.2 Manifest v3.1 (kwargs now honoured)

The `update_dataset()` function in `mal_core/download/manifest.py:62`
now honours every kwarg (`type`, `required_for_abm`, `variables`,
`format`, `period`). The v3.1 schema adds:

| Field | Type | Notes |
|---|---|---|
| `period` | `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}` | Optional. For multi-year NC entries (e.g. daily rainfall across 2024–2025). Used by `validate_completeness` to check year coverage instead of individual file existence. |
| `schema_version` | `str` | Reserved for future migration. Not yet written by v3.1. |

**Historical note**: §6.2 previously documented a drift where `update_dataset` accepted but ignored kwargs. This was fixed — all kwargs are now written to disk. The `register_dataset` helper in `_shared.py` calls `update_dataset` with kwargs directly.

### §6.3 Dataset types and registered loaders

| Type | Format | Frequency | Pattern | Registered loader | `required_for_abm` |
|---|---|---|---|---|---|
| `env` | NetCDF4 | daily | `<aoi>_regional_<start>_<end>_env.nc` | `daily_nc` (assembles chirps+jrc_gsw+era5+modis) | yes |
| `env` (COG variant) | GeoTIFF | monthly | `<aoi>_<scale>_<year>_<month:02d>_env.tif` | ingest (`output_format="tif"`) | yes |
| `chirps_rainfall` | GeoTIFF | monthly | `<aoi>_rainfall_<year>.tif` | `chirps` | no |
| `chirps_rainfall_daily` | NetCDF4 | daily | `<aoi>_rainfall_daily_<start>_<end>_daily.nc` | `chirps` (`load_chirps_rainfall_daily`) | yes |
| `era5_temp` | GeoTIFF | monthly | `<aoi>_temp_suitability_<year>.tif` | `era5` (`load_era5_temp_suitability`) | no |
| `era5_water_temp` | GeoTIFF | monthly | `<aoi>_water_temp_<year>.tif` | `era5` (`load_era5_water_temp`) | no |
| `wind` | NetCDF4 | 6-hourly | `<aoi>_wind_6hourly_<year>.nc` | `era5` (`load_era5_wind_6hourly`) | no |
| `modis_ndvi` | GeoTIFF | monthly | `<aoi>_ndvi_<year>.tif` | `modis` | no |
| `habitat` | GeoPackage | static/time-series | `<aoi>_regional_<year>_<month>_habitat_patches.gpkg` | ingest (built from DEM+TWI) | yes |
| `dem` | GeoTIFF | static | `<aoi>_elevation.tif` | `dem` (`load_merit_dem`) | no |
| `jrc_water` | GeoTIFF | static | `<aoi>_water_occurrence.tif` | `jrc_gsw` | no |
| `worldpop` | GeoTIFF | static | `<aoi>_population.tif` | `worldpop` | no |
| `glw_cattle` | GeoTIFF | static | `<aoi>_cattle.tif` | `glw` (`load_glw_livestock`) | no |
| `glw_goats` | GeoTIFF | static | `<aoi>_goats.tif` | `glw` | no |
| `glw_sheep` | GeoTIFF | static | `<aoi>_sheep.tif` | `glw` | no |
| `glw_pigs` | GeoTIFF | static | `<aoi>_pigs.tif` | `glw` | no |
| `glw_chickens` | GeoTIFF | static | `<aoi>_chickens.tif` | `glw` | no |
| `ghsl_urban` | GeoTIFF | static | `<aoi>_urban_class.tif` | `ghsl` | no |
| `host_static` | NetCDF4 | static | `<aoi>_host_static.nc` | ingest (built from WorldPop+GLW+GHSL+buildings+wildlife) | yes |
| `host_manifest` | JSON | static | `<aoi>_host_manifest.json` | ingest | yes |
| `wildlife_proxy` | GeoTIFF | static | `<aoi>_wildlife_host_proxy.tif` | `wildlife` | no |
| `buildings` | GeoTIFF | static | `<aoi>_building_fraction.tif` | `buildings` (Overture Maps) | no |
| `mobility_day` | CSR | static | `<aoi>_mobility_day.csr` | ingest (built from host_static) | no |
| `mobility_night` | CSR | static | `<aoi>_mobility_night.csr` | ingest | no |
| `livestock_mobility` | CSR | static | `<aoi>_livestock_mobility.csr` | ingest | no |

**Deprecated**: `worldcover` — archived to `mal-commonlib/.../loaders/_legacy/worldcover.py`. Use `jrc_gsw` for `water_frac`.

## 7. Migration & deprecation

- **Manifest v1 → v2**: auto on read, manual via `scripts/migrate_data_format.py` on disk. No further writes should produce v1.
- **Manifest v2 → v3.1**: writes always produce v3.1 (all kwargs honoured, `period` field supported). Reads auto-migrate v1/v2 in memory.
- **Env COG `contract_version: "1.0"` vs NetCDF `contract_version: "2.0"`**: the COG path is the M1/M2 contract pinned in `abm/spec.md` §5.2; the NetCDF path is a richer daily CF-1.8 surface used by some consumers. Bumping either without bumping the other is a P1 bug — see drift check.
- **Deprecated**: `worldcover` dataset — archived to `mal-commonlib/.../loaders/_legacy/worldcover.py`. Use `jrc_gsw` for `water_frac`.
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1..4: file naming convention is enforced
uv run python -c "
import re, json
from pathlib import Path
for m in Path('data').glob('*/manifest.json'):
    aoi = m.parent.name
    ts = re.compile(rf'^{aoi}_[a-z0-9_]+_\d{{4}}\.[a-z]+$')
    st = re.compile(rf'^{aoi}_[a-z0-9_]+\.[a-z]+$')
    for f in json.loads(m.read_text()).get('expected_files', []):
        assert ts.match(f) or st.match(f), f'bad name {f} for aoi {aoi}'
"

# INV-5..7: every manifest has datasets + expected_files
uv run python -c "
import json
from pathlib import Path
for m in Path('data').glob('*/manifest.json'):
    d = json.loads(m.read_text())
    assert 'datasets' in d and 'expected_files' in d, f'bad schema in {m}'
"

# INV-8: no v1 manifests survive
rg '"files"\s*:\s*\{[^}]*"ghana' data/ && echo "FAIL: v1 manifest found" || echo "OK"

# INV-10..12: env tensors honour NoData and band order
uv run python -c "
import xarray as xr, rasterio
for p in __import__('pathlib').Path('data/ghana').glob('*env*.nc'):
    ds = xr.open_dataset(p)
    assert float(ds['rainfall'].encoding.get('_FillValue', -9999.0)) == -9999.0
for p in __import__('pathlib').Path('data/ghana').glob('*_env.tif'):
    with rasterio.open(p) as src:
        assert src.nodata == -9999.0
        names = src.descriptions
        assert names[0] == 'water_frac' and names[-1] == 'ndvi', f'bad band order: {names}'
"

# INV-13..15: loaders return xr objects in memory
rg "def\s+load_\w+\(" mal-commonlib/src/mal_commonlib/data/loaders/ | wc -l
```

## 9. Examples

```python
from mal_core.download.manifest import (
    read_manifest, update_dataset, validate_completeness, get_dataset_files,
)
from mal_commonlib.aoi import AOI

aoi = AOI.from_slug("ghana")

# Resolve the env file for 2024
paths = get_dataset_files(aoi.slug, "env", year=2024)
assert paths and paths[0].exists(), "missing env; run `malariasim download --aoi ghana --datasets era5,chirps,jrc_gsw,modis --years 2024`"

# Block the ABM from starting until completeness holds
missing = validate_completeness(aoi.slug)
assert not missing, f"missing: {missing}"
```

```python
# Loader returns in-memory data — never writes to disk
from mal_commonlib.data.loaders.era5 import load_era5_temp_suitability
da = load_era5_temp_suitability(AOI.from_slug("ghana"), years=[2024], months=[7])
assert da.dtype == "float32"
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `commonlib`, `download`, `ingest`, `abm`, `training`, `prediction`, `pipeline`, `scoring`.
- External: CF-1.8 conventions (NetCDF); GeoTIFF spec.