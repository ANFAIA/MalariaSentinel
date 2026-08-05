# commonlib Spec

> Foundation layer. Owns AOI, paths, config, terrain (TWI), and reusable
> data utilities (host loaders, mobility). No domain logic, no ABM, no
> pipeline orchestration.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: download
    direction: bidirectional
    reason: download uses AOI + paths from commonlib; commonlib consumes downloaded xr objects via data utils
    severity: breaking
  - target: ingest
    direction: downstream
    reason: ingest imports AOI, terrain (TWI), and data utils from commonlib
    severity: breaking
  - target: abm
    direction: downstream
    reason: ABM consumes AOI + paths; AOI.cells_per_side pins the (H, W) shape
    severity: breaking
  - target: training
    direction: downstream
    reason: training reads rollouts whose AOI shape comes from commonlib.AOI
    severity: breaking
  - target: prediction
    direction: downstream
    reason: prediction needs AOI + grid resolution to instantiate the U-Net input window
    severity: breaking
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
| Component | `mal-commonlib/src/mal_commonlib/` |
| Version | `v0.1.0` |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-08-05` |

## 1. Objective

`mal-commonlib` is the cross-pipeline substrate. It provides the
**AOI**, the repo-relative **paths**, the **TWI** terrain computation,
and the **data utilities** (host loaders, mobility helpers) that every
other spec assumes exist. Without it, the ABM, ingest, training, and
prediction layers would all reinvent bbox/CRS handling and the TWI
formula.

The package carries **no** domain logic — it does not know what
malaria is, does not call the ABM, does not own the manifest. It is
imported by everything else.

## 2. In scope

- `AOI` and `Scale` (region-agnostic, M1.2a). Frozen Pydantic model.
- TWI computation from a DEM (`compute_twi`, pure numpy/scipy).
- Repo path constants (`REPO_ROOT`, `DATA_DIR`, `PAPERS_DIR`, `TERRAIN_DIR`, `RUNS_DIR`).
- Simulation/training parameters and utility functions (`config.py`).
- Data utilities (`data/utils.py`, `data/host_utils.py`, `data/mobility.py`).
- Data loaders (`data/loaders/*.py`) — JRC GSW, WorldPop, GLW, GHSL, wildlife, buildings, CHIRPS, DEM, ERA5, MODIS.
- Slug registry inside `AOI.from_slug` (current entry: `ghana`).

## 3. Out of scope

- Manifest schema → `docs/specs/data/spec.md`.
- DOWNLOADER dict convention → `docs/specs/download/spec.md`.
- ABM C++ engine + Mesa-Geo adapter → `docs/specs/abm/spec.md`.

## 4. Public API

### 4.1 AOI & Scale (`mal_commonlib.aoi`)

| Symbol | Notes |
|---|---|
| `AOI` | Frozen Pydantic model. `slug` matches `[a-z0-9]+(-[a-z0-9]+)*`. `bbox = (west, south, east, north)` with `west < east`, `south < north`. `crs` must parse via `pyproj.CRS.from_user_input`. `resolution_m > 0`. `scale` ∈ `{REGIONAL, NATIONAL, CONTINENTAL}`. |
| `Scale` | Enum: `REGIONAL` (1 km, raw raster), `NATIONAL` (GADM-2 mean-pool), `CONTINENTAL` (5 km + GADM-0 mean-pool, U-Net only). |
| `AOI.cells_per_side()` | `(H, W)` cells to cover `bbox` at `resolution_m`, rounded up. **Pin for the ABM output tensor shape.** |
| `AOI.from_slug(slug)` | Build from the in-code registry. `ghana` is the only entry today. Adding entries here is a non-breaking change. |
| `AOI.from_bbox(...)` | Build from an explicit bbox + CRS + slug + resolution. |
| `AOI.from_gadm(...)` | Build from GADM shapefile. Resolves `gadm_path` via arg or `MAL_GADM_PATH` env. |
| `AOI.to_file(path)` | Serialize to JSON. Returns the written `Path`. |
| `AOI.from_file(path)` | Inverse of `to_file`. |
| `AOI.crs_obj` | Property: parsed `pyproj.CRS` object. |
| `AOI.width_m` | Property: bbox width in metres (geographic CRS → great-circle conversion). |
| `AOI.height_m` | Property: bbox height in metres. |
| `AOI.area_km2` | Property: bbox area in km². |
| `AOI.geom` | Property: bbox as a `shapely.geometry.Polygon`. |
| `AOI.to_geoseries(crs=None)` | bbox as a `gpd.GeoSeries`. |

### 4.2 TWI (`mal_commonlib.terrain.twi`)

| Symbol | Notes |
|---|---|
| `compute_twi(dem, *, cell_size_m=None)` | D8 + central-difference slope. Returns `xr.DataArray`, dtype `float32`, NoData `-9999.0`. |
| `NODATA_OUT` | Module-level constant: `-9999.0`. |

### 4.3 Config & paths (`mal_commonlib.config`)

| Symbol | Notes |
|---|---|
| `REPO_ROOT`, `DATA_DIR`, `PAPERS_DIR`, `TERRAIN_DIR`, `RUNS_DIR` | Repo-relative paths, computed from `__file__`. `RUNS_DIR` is created at import. |
| `DATA_REGIONS` | Dict of known dataset region keys → descriptions. |
| `DST_CRS`, `DST_RES` | Default target CRS (`EPSG:32630`) and resolution (1000 m). |
| `LAYER_FILES` | Dict mapping layer names to filenames. |
| `SimParams` | Dataclass holding one parameter set for a simulation rollout. |
| `PARAM_RANGES` | Dict of parameter → `(min, max)` ranges for training randomisation. |
| Simulation/training constants | `K_MAX`, `WATER_THRESH`, `MU`, `R_MAX`, `N_STEPS`, `PATCH`, `STRIDE`, `UNET_CHANNELS`, `LOSS_DICE_WEIGHT`, `TRAIN_EPOCHS`, `TRAIN_LR`, `TRAIN_BATCH`, `N_ROLLOUTS`, etc. |

### 4.4 Host utilities (`mal_commonlib.data.host_utils`)

| Symbol | Notes |
|---|---|
| `aggregate_to_grid(source, source_transform, source_crs, target_transform, target_crs, target_shape, method="sum", nodata=-9999.0)` | Conservative (sum-preserving) or nearest-neighbour resampling of a source raster to the ABM grid via `rasterio.warp.reproject`. |
| `build_host_static_nc(human, cattle, goats, sheep, urban_class, output_path, grid_spec, *, pigs=None, chickens=None, building_fraction=None, wildlife_host_proxy=None)` | Write the static host density NetCDF (5 core + 4 optional variables) for the ABM engine. |
| `write_manifest(output_path, human, cattle, goats, sheep, urban_class, grid_spec, *, pigs=None, chickens=None, building_fraction=None, wildlife_host_proxy=None)` | Write a JSON manifest with summary statistics for the host static NetCDF. |

### 4.5 Mobility utilities (`mal_commonlib.data.mobility`)

| Symbol | Notes |
|---|---|
| `build_gravity_od(attractiveness, cell_size_km, beta, max_distance_km=50.0, sparsity_threshold=1e-6)` | Row-stochastic sparse OD matrix from a gravity model. Returns `(row_ptr, col_idx, values, n_rows, n_cols)` CSR arrays. |
| `build_identity_od(n_cells)` | Identity OD matrix (everyone stays home). |
| `write_csr(row_ptr, col_idx, values, n_rows, n_cols, path)` | Write sparse OD matrix in CSR binary format (little-endian, compatible with C++ `SparseOD::load_from_csr`). |

### 4.6 Data utilities (`mal_commonlib.data.utils`)

| Symbol | Notes |
|---|---|
| `read_raster(path)` | Open a raster, mask nodata, return a squeezed `DataArray`. |
| `reproject_to_grid(src_path, ref, name="layer")` | Reproject a raster to match a reference grid, applying nodata policy. |
| `points_to_grid(lats, lons, affine, crs)` | Map lon/lat occurrence points to grid (row, col) in a projected grid. |
| `norm_minmax(a)` | Min-max normalisation to [0, 1]. |

### 4.7 Data loaders (`mal_commonlib.data.loaders.<name>`)

Function-style loaders. Each module exports a public `load_*` function. The loader registry (`loaders/__init__.py`) re-exports these plus deprecated class-style shims.

| Module | Function | Dataset |
|---|---|---|
| `jrc_gsw` | `load_jrc_gsw_water_frac` | JRC Global Surface Water — water occurrence fraction |
| `worldpop` | `load_worldpop_population` | WorldPop population density |
| `glw` | `load_glw_livestock` | FAO Gridded Livestock of the World v4 |
| `ghsl` | `load_ghsl_urban_class` | GHS-SMOD settlement classification |
| `wildlife` | `load_wildlife_host_proxy` | Wildlife host suitability proxy |
| `buildings` | `load_buildings_fraction` | Overture Maps building footprint fraction |
| `chirps` | `load_chirps_rainfall`, `load_chirps_rainfall_daily` | CHIRPS rainfall (monthly and daily) |
| `dem` | `load_merit_dem` | MERIT DEM elevation |
| `era5` | `load_era5_temp_suitability`, `load_era5_water_temp`, `load_era5_wind_6hourly` | ERA5-Land (temperature, water temp, wind) |
| `modis` | `load_modis_ndvi` | MODIS NDVI (MOD13A3) |

> **Internal/legacy:** `_legacy/worldcover.py` provides `load_worldcover_water_frac` (ESA WorldCover water fraction). Not re-exported from `loaders.__init__`.

## 5. Invariants

- **INV-1.** `AOI` is frozen (`model_config = {"frozen": True}`). Mutating `aoi.bbox = ...` raises.
- **INV-2.** `AOI.slug` always matches `[a-z0-9]+(-[a-z0-9]+)*`.
- **INV-3.** `AOI.bbox` always satisfies `west < east ∧ south < north`.
- **INV-4.** `AOI.crs` is always parseable by `pyproj.CRS.from_user_input`.
- **INV-5.** `compute_twi` output dtype is `float32` and NoData sentinel is exactly `-9999.0`.
- **INV-6.** `AOI.cells_per_side()` is the single source of truth for the ABM output `(H, W)`. Any code that hardcodes `H = W = 128` outside `commonlib` is a drift bug.
- **INV-7.** `RUNS_DIR` exists after import of `mal_commonlib.config`.
- **INV-8.** `build_host_static_nc` output NetCDF contains CF-1.8 conventions with CRS coordinate variable.
- **INV-9.** `write_csr` output is little-endian binary compatible with C++ `SparseOD::load_from_csr()`.
- **INV-10.** All loaders return `xr.DataArray` with dims `(y, x)` and dtype `float32`.

## 6. Data contracts

- `AOI.to_file(path)` writes a JSON payload with keys `slug`, `name`, `bbox`, `crs`, `resolution_m`, `scale`, `gadm_id`. `AOI.from_file(path)` is the inverse.
- `compute_twi` input: `xr.DataArray` with dims `(y, x)`, dtype coercible to `float32`. Output: same dims, `float32`, NoData `-9999.0`, attrs `long_name="Topographic Wetness Index"`, `source="D8 + central-difference slope (Beven & Kirkby 1979)"`.
- `build_host_static_nc` output: NetCDF4 with CF-1.8 conventions. Core vars `human`, `cattle`, `goats`, `sheep` (float32, persons/animals per cell), `urban_class` (int32, GHS-SMOD codes). Optional vars: `pigs`, `chickens`, `building_fraction`, `wildlife_host_proxy`. Global attrs include CRS WKT, grid transform, nodata sentinel.
- `write_csr` output: little-endian binary — `[int32 n_rows, int32 n_cols, int32 nnz, int32×(n_rows+1) row_ptr, int32×nnz col_idx, float32×nnz values]`. Compatible with C++ `SparseOD::load_from_csr()`.
- Loaders return `xr.DataArray | xr.Dataset` in memory (see `download/spec.md` §4 for the canonical signature).

## 7. Migration & deprecation

- Adding a new `Scale` value → bump MINOR (additive).
- Adding a new slug to `AOI.from_slug`'s registry → PATCH (data, not API).
- Renaming `AOI` field → bump MAJOR.
- Changing TWI formula → bump MAJOR (output consumers are pinned).
- Deprecation policy: 1 MINOR version carries the deprecation warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1: AOI is frozen
uv run python -c "from mal_commonlib.aoi import AOI; a = AOI.from_slug('ghana'); a.bbox = (0,0,0,0); print('FAIL: not frozen')"

# INV-2/3/4: validator surface
uv run pytest mal-commonlib/tests/test_aoi.py -v

# INV-5: TWI output contract
uv run pytest mal-commonlib/tests/test_twi.py -v

# INV-6: cells_per_side is the only source of (H, W)
rg "H\s*=\s*W\s*=\s*128|H\s*=\s*128|W\s*=\s*128" mal-core/src/ mal-execution/src/ | grep -v tests

# INV-7: paths exist
test -d "$(uv run python -c 'from mal_commonlib.config import RUNS_DIR; print(RUNS_DIR)')"

# INV-10: loader contract
uv run pytest mal-commonlib/tests/test_host_loaders.py -v
```

## 9. Examples

```python
from mal_commonlib.aoi import AOI, Scale

# Canonical construction
aoi = AOI.from_slug("ghana")
assert aoi.scale == Scale.REGIONAL
H, W = aoi.cells_per_side()  # drives the ABM output tensor shape

# Geometry helpers
print(f"{aoi.area_km2:.0f} km², {aoi.width_m/1000:.0f} km × {aoi.height_m/1000:.0f} km")

# Round-trip via JSON
aoi.to_file("data/ghana/aoi.json")
aoi2 = AOI.from_file("data/ghana/aoi.json")
assert aoi2 == aoi
```

```python
import xarray as xr
from mal_commonlib.terrain.twi import compute_twi

dem = xr.open_dataarray("terrain/ghana_dem.tif")
twi = compute_twi(dem, cell_size_m=1000)
assert twi.dtype == "float32"
assert float(twi.rio.nodata) == -9999.0
```

```python
import numpy as np
from mal_commonlib.data.host_utils import build_host_static_nc
from rasterio.transform import from_bounds

grid_spec = {
    "crs": "EPSG:32630",
    "transform": from_bounds(0, 0, 100000, 100000, 100, 100),
    "height": 100,
    "width": 100,
}
human = np.ones((100, 100), dtype=np.float32) * 50
# ... other arrays ...
build_host_static_nc(human, human, human, human, np.ones((100, 100), dtype=np.int32) * 50,
                     "output/host_density.nc", grid_spec)
```

```python
from mal_commonlib.data.mobility import build_gravity_od, write_csr

attractiveness = np.random.rand(100, 100).astype(np.float32)
row_ptr, col_idx, values, nr, nc = build_gravity_od(attractiveness, 1.0, 0.5)
write_csr(row_ptr, col_idx, values, nr, nc, "output/mobility.csr")
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30` (spec template + affects block).
- Specs (by folder): `data`, `download`, `ingest`, `abm`, `training`, `prediction`.
- External: Beven & Kirkby (1979) — TWI reference formulation.