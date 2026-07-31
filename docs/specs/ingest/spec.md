# ingest Spec

> Owns the **build stage**: turning the raw inputs (downloaded by
> `download`) into the ABM-ready artefacts — env tensor, habitat
> patches, host density, mobility OD matrices. Sits between
> `download` and `abm` in the pipeline.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: download
    direction: upstream
    reason: ingest consumes raw inputs produced by download (env vars, dem, jrc, modis, worldpop, glw, ghsl, buildings, wildlife)
    severity: breaking
  - target: abm
    direction: upstream
    reason: ABM reads env tensor (COG/NC), habitat gpkg, host_static.nc, mobility CSR; ingest pins band order and shape
    severity: breaking
  - target: training
    direction: downstream
    reason: training's env tensor contract is the COG written by ingest; channel names must match
    severity: breaking
  - target: prediction
    direction: downstream
    reason: prediction's env_loader consumes NetCDF env vars; ingest's NC variant is the canonical producer
    severity: breaking
  - target: data
    direction: bidirectional
    reason: ingest writes to data/<aoi>/ and registers files via update_dataset; obeys naming spec
    severity: breaking
  - target: commonlib
    direction: upstream
    reason: ingest imports AOI, Scale, TWI, host_utils, mobility helpers from commonlib
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
| Component | `mal-core/src/mal_core/ingest/` |
| Version | `v1.0` (env COG); `v1.0` (env NetCDF); `v1.0` (hosts); `v1.0` (mobility) |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

Ingest is the **transform layer** that turns heterogeneous raw
inputs (ERA5 reanalysis, CHIRPS rainfall, MERIT DEM, JRC water
occurrence, MODIS NDVI, WorldPop, GLW livestock, GHSL urban, Overture
buildings, wildlife proxies) into the three ABM-ready artefacts:

1. **Env tensor** (4-band raster or daily NetCDF).
2. **Habitat patches** (GeoPackage of candidate oviposition cells).
3. **Host density** (static NetCDF: humans + 5 livestock species + urban_class + building_fraction + wildlife_proxy).
4. **Mobility OD matrices** (3 CSR files: day, night, livestock).

Without ingest the ABM would have to inline the geometry,
reprojection, and aggregation of 8+ datasets on every run. Ingest
makes the ABM consume a single, deterministic, manifest-resolvable
shape per AOI.

## 2. In scope

- `build_env_tensor(aoi, year, month, output_dir, *, scale="regional", output_format="tif"|"nc", twi_threshold=8.0, skip_era5=False, skip_modis=False, skip_jrc_gsw=False) -> dict` — writes env raster/NC + habitat patches.
- `build_host_dataset(aoi, *, output_dir, worldpop_year=2019, skip_buildings=False, skip_wildlife=False) -> dict` — writes host_static.nc + host_manifest.json.
- `build_mobility_dataset(hosts_path, *, output_dir, aoi_slug, cell_size_km=1.0, beta_day=0.05, beta_night=0.5, beta_livestock=0.1, max_distance_km=50.0) -> dict` — writes 3 CSR files + mobility_manifest.json.
- Flag schema (`INGEST_FLAGS_SCHEMA`, `IngestFlags`) covering env + hosts + mobility.
- Slug registry in `_shared._DEFAULT_REGISTRY` (currently just `ghana`).
- `safe_load` (graceful loader wrapper that fills with NoData on auth/network failure).
- `empty_channel` (NoData-fill helper).
- `register_dataset` (writes through to manifest).
- Pipeline position: stage 2 (after download). Three builders: build_env_tensor, build_host_dataset, build_mobility_dataset.

## 3. Out of scope

- Raw data fetching → `docs/specs/download/spec.md`.
- ABM consumption semantics → `docs/specs/abm/spec.md`.
- File naming on disk → `docs/specs/data/spec.md`.
- AOI definition → `docs/specs/commonlib/spec.md`.
- No orchestrator in mal-core; GUI/agent layer may add one.
- TWI computation itself → `docs/specs/commonlib/spec.md` (ingest only consumes `compute_twi`).

## 4. Public API

### `build_env_tensor`

```python
def build_env_tensor(
    aoi: str | AOI,
    year: int,
    month: int,
    output_dir: Path,
    *,
    scale: str = "regional",
    skip_era5: bool = False,
    skip_modis: bool = False,
    skip_jrc_gsw: bool = False,
    output_format: str = "tif",     # "tif" (COG) or "nc" (CF-1.8 daily)
    name: str | None = None,
    twi_threshold: float = 8.0,
) -> dict:
    """Returns {"env_path", "habitat_path", "aoi_slug", "scale", "grid", "year", "month", "format"}."""
```

### `build_host_dataset`

```python
def build_host_dataset(
    aoi: AOI,
    *,
    output_dir: Path,
    worldpop_year: int = 2019,
    cache_dir: Path | None = None,
    skip_buildings: bool = False,
    skip_wildlife: bool = False,
) -> dict:
    """Returns {"nc_path", "manifest_path", "human_total", "livestock_total", "urban_cells", "rural_cells", "grid"}."""
```

### `build_mobility_dataset`

```python
def build_mobility_dataset(
    hosts_path: Path,
    *,
    output_dir: Path,
    aoi_slug: str = "ghana",
    cell_size_km: float = 1.0,
    beta_day: float = 0.05,
    beta_night: float = 0.5,
    beta_livestock: float = 0.1,
    max_distance_km: float = 50.0,
) -> dict:
    """Returns {"files", "manifest_path", "n_cells", "human_total", "livestock_total", "build_time_s"}."""
```

## 5. Invariants

### §5.1 Env tensor (COG)

- **INV-1.** Bands in order: `water_frac, rainfall, temp_suitability, ndvi` (matches `abm/spec.md` §5.2 INV-6).
- **INV-2.** `dtype = float32`, NoData `-9999.0`, tile `128×128`, deflate compression, `blockxsize=128, blockysize=128`.
- **INV-3.** Shape `(4, H, W)` where `(H, W) = aoi.cells_per_side()`.
- **INV-4.** Sidecar carries `band_names`, `nodata`, `shape`, `contract_version: "1.0"`, `generator_version: "m1-thin-0.1.0"`, `crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `abm_params_hash`.
- **INV-5.** File naming: `{aoi_slug}_{scale}_{year:04d}_{month:02d}_env.tif`.
- **INV-6.** Habitat patches: `(TWI > twi_threshold) ∧ (water_frac > 0) ∧ isfinite(TWI)` → GeoPackage with columns `twi_value, water_frac_value, row, col, aoi_slug, geometry`. CRS = AOI CRS.

### §5.2 Env tensor (NetCDF)

- **INV-7.** CF-1.8 conventions, dims `(time, y, x)`, vars `rainfall, water_temp_c, water_frac, ndvi` with `_FillValue = -9999.0`, `dtype = float32`, `zlib=True, complevel=4`.
- **INV-8.** `time` axis covers the full month (`calendar.monthrange(year, month)[1]` days), with explicit CF time units.
- **INV-9.** `contract_version: "2.0"`, `generator_version: "m2-daily-0.1.0"`. **Differs from COG INV-4** — see §7.
- **INV-10.** File naming: `{aoi_slug}_{scale}_{year:04d}_{month:02d}_env.nc`.

### §5.3 Host dataset

- **INV-11.** File: `{aoi_slug}_host_static.nc`. Variables: `human, cattle, goats, sheep, pigs, chickens, urban_class (int32), building_fraction, wildlife_host_proxy`. All 2D, shape `(H, W)`.
- **INV-12.** Companion: `{aoi_slug}_host_manifest.json` (human_total, livestock totals per species, urban/rural cell counts, grid spec, etc.).
- **INV-13.** Urban class reclassification: GHSL SMOD R2023A `30 → 30` (urban), `20-29 → 50` (rural), `0-19 → 20` (water). Failure falls back to all-50 (rural).
- **INV-14.** Building/wildlife fallback values: `building_fraction = 0.6 if urban else 0.1`; `wildlife_proxy = 0.3`. These constants are pinned here.

### §5.4 Mobility

- **INV-15.** Three CSR files: `{aoi_slug}_mobility_day.csr`, `{aoi_slug}_mobility_night.csr`, `{aoi_slug}_livestock_mobility.csr`. Gravity model with `cell_size_km=1.0`, `beta_day=0.05`, `beta_night=0.5`, `beta_livestock=0.1`, `max_distance_km=50.0`.
- **INV-16.** `build_mobility_dataset` requires the host_static.nc from §5.3. If the file is missing → `FileNotFoundError`.

### §5.5 NoData & resilience

- **INV-17.** Any loader failure (auth missing, network, file not found) is caught by `safe_load` and replaced with a NoData-filled channel of the correct shape (`empty_channel`). The ingest stage never aborts because of a missing loader.
- **INV-18.** `NODATA_SENTINEL = -9999.0` is the single value used across all ingest outputs (rasters, NetCDF fill, sidecar nodata).

### §5.6 Manifest integration

- **INV-19.** Each builder registers its outputs in the manifest via `_shared.register_dataset`, which delegates to `update_dataset` in `data/spec.md`. See §6.2 in `data/spec.md` for the known kwargs-ignored drift — ingest assumes the kwargs (`type`, `required_for_abm`, `variables`, `format`) reach disk; today they don't.

## 6. Data contracts

- Outputs land under `output_dir/...` per §5. Naming per `data/spec.md` §5.1.
- Loader calls conform to `download/spec.md` §4 and §5.1.
- CRS: ingest assumes the AOI's CRS. Reprojection from a loader's native CRS to the AOI CRS is done by `aggregate_to_grid` (in `mal_commonlib.data.host_utils`).

## 7. Migration & deprecation

- **Env COG vs NC `contract_version` mismatch** (COG = 1.0, NC = 2.0): this is **deliberate** today (the NC is a richer surface). Bumping the COG requires updating `abm/spec.md` §5.2 readers and `prediction/spec.md` env loaders. Recorded as drift until a single contract_version unifies them (post-M11).
- **GHSL SMOD reclassification** (§5.3 INV-13) is hardcoded. Adding a new SMOD version (R2024A, …) is a MINOR change.
- Adding a new env band → MAJOR (training and prediction read by band name, but the band order is part of the contract).
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1/2: COG env tensor band order + dtype + NoData
uv run python -c "
import rasterio
from pathlib import Path
for p in Path('data/ghana').glob('*_env.tif'):
    with rasterio.open(p) as src:
        assert src.nodata == -9999.0, f'{p}: nodata={src.nodata}'
        assert src.descriptions == ('water_frac','rainfall','temp_suitability','ndvi'), f'{p}: bands={src.descriptions}'
        assert src.dtypes[0] == 'float32'
"

# INV-7/8: NC env tensor CF-1.8 + fill value
uv run python -c "
import xarray as xr
from pathlib import Path
for p in Path('data/ghana').glob('*_env.nc'):
    ds = xr.open_dataset(p)
    assert ds.attrs.get('Conventions') == 'CF-1.8'
    assert 'time' in ds.dims
    for v in ('rainfall','water_temp_c','water_frac','ndvi'):
        assert float(ds[v].encoding['_FillValue']) == -9999.0
"

# INV-11/12: host_static.nc has all expected vars + manifest exists
uv run python -c "
import xarray as xr, json
from pathlib import Path
for p in Path('data/ghana').glob('*_host_static.nc'):
    ds = xr.open_dataset(p)
    for v in ('human','cattle','goats','sheep','pigs','chickens','urban_class','building_fraction','wildlife_host_proxy'):
        assert v in ds.data_vars, f'{p}: missing {v}'
    sidecar = p.with_name(p.stem.replace('_host_static','') + '_host_manifest.json')
    assert sidecar.exists(), f'missing {sidecar}'
"

# INV-15: mobility CSRs exist with expected naming
uv run python -c "
from pathlib import Path
for p in Path('data/ghana').glob('*mobility_day.csr'): pass
for p in Path('data/ghana').glob('*mobility_night.csr'): pass
for p in Path('data/ghana').glob('*livestock_mobility.csr'): pass
"

# INV-17: NoData sentinel is the only one used
rg -l "NODATA_SENTINEL" mal-core/src/mal_core/ingest/
rg "[-]?9999\.0|255" mal-core/src/mal_core/ingest/ | grep -v _shared.py | grep -v NODATA_SENTINEL
```

## 9. Examples

```python
# Build env + habitat for a single AOI/month
from pathlib import Path
from mal_core.ingest import build_env_tensor
build_env_tensor("ghana", 2024, 7, Path("runs/ingest"), output_format="tif")
# -> writes runs/ingest/ghana_regional_2024_07_env.tif + ..._habitat_patches.gpkg
```

```python
# Build hosts (separate stage)
from pathlib import Path
from mal_commonlib.aoi import AOI
from mal_core.ingest.hosts import build_host_dataset
build_host_dataset(AOI.from_slug("ghana"), output_dir=Path("runs/hosts"))
# -> runs/hosts/ghana_host_static.nc + ghana_host_manifest.json
```

```python
# Build mobility (third stage; needs host_static.nc from the previous stage)
from pathlib import Path
from mal_core.ingest.mobility import build_mobility_dataset
build_mobility_dataset(
    hosts_path=Path("runs/hosts/ghana_host_static.nc"),
    output_dir=Path("runs/mobility"),
    aoi_slug="ghana",
)
# -> runs/mobility/ghana_mobility_day.csr + ..._mobility_night.csr + ..._livestock_mobility.csr
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `commonlib`, `download`, `data`, `abm`, `training`, `prediction`, `pipeline`.
- Plan: `m11-pipeline-unification` (covers the kwargs-ignored drift in §5.6 INV-19).
- External: GHSL SMOD R2023A reclassification table.