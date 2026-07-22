---
name: mal-commonlib-api
description: Expert guide to all shared utilities in mal-commonlib — config constants, AOI schema, data loaders (DEM, CHIRPS, ERA5, JRC GSW, MODIS, WorldCover), terrain TWI, and data utilities. Use this skill when working with any mal-commonlib module, writing code that imports from mal_commonlib, or needing to understand what public APIs are available in the foundation package.
---

# mal-commonlib API Reference

Foundation package for MalariaSentinel. No internal dependencies — everything here is safe to import from any other package in the monorepo.

## Module index

| Module | Import path | What it provides |
|---|---|---|
| **config** | `mal_commonlib.config` | Paths, AOI bounds, CRS, layer files, simulation params, thermal response, U-Net params |
| **AOI** | `mal_commonlib.aoi` (also re-exported from `mal_commonlib`) | Region-agnostic Area of Interest schema |
| **Data loaders** | `mal_commonlib.data.loaders` | `load_jrc_gsw_water_frac`, `load_worldcover_water_frac` (plus individual modules) |
| **DEM loader** | `mal_commonlib.data.loaders.dem` | `load_merit_dem` — MERIT DEM 90 m with NASADEM fallback |
| **CHIRPS loader** | `mal_commonlib.data.loaders.chirps` | `load_chirps_rainfall`, `load_chirps_rainfall_daily` — CHIRPS v2.0 precipitation |
| **ERA5 loader** | `mal_commonlib.data.loaders.era5` | `load_era5_temp_suitability`, `load_era5_water_temp`, `sharpe_demichele_growth` |
| **JRC GSW loader** | `mal_commonlib.data.loaders.jrc_gsw` | `load_jrc_gsw_water_frac` — JRC Global Surface Water 30 m |
| **MODIS loader** | `mal_commonlib.data.loaders.modis` | `load_modis_ndvi` — MODIS MOD13A3 v061 monthly NDVI |
| **WorldCover loader** | `mal_commonlib.data.loaders.worldcover` | `load_worldcover_water_frac` — ESA WorldCover 10 m |
| **TWI** | `mal_commonlib.terrain.twi` | `compute_twi` — Topographic Wetness Index from DEM |
| **Data utils** | `mal_commonlib.data.utils` | `read_raster`, `reproject_to_grid`, `points_to_grid`, `norm_minmax` |

---

## config — Configuration constants

```python
from mal_commonlib import config as C
```

### Paths

| Constant | Value | Description |
|---|---|---|
| `REPO_ROOT` | `Path(__file__).resolve().parents[3]` | Project root |
| `DATA_DIR` | `REPO_ROOT / "data"` | Datasets directory |
| `PAPERS_DIR` | `REPO_ROOT / "papers"` | Research papers |
| `TERRAIN_DIR` | `REPO_ROOT / "terrain"` | DEM tiles |
| `RUNS_DIR` | `REPO_ROOT / "runs"` | Experiment outputs (auto-created) |
| `LAYER_DIR` | `RUNS_DIR / "layers"` | Raster layers (auto-created) |
| `STACK_CACHE` | `RUNS_DIR / "env_stack.npz"` | Cached env stack |

### AOI & grid

| Constant | Value | Description |
|---|---|---|
| `AOI_W, AOI_E, AOI_S, AOI_N` | `-2.97, 0.79, 4.69, 9.79` | Ghana bounding box (degrees) |
| `DST_CRS` | `"EPSG:32630"` | UTM zone 30N |
| `DST_RES` | `1000` | Working grid resolution (metres) |

### Environmental layer files

```python
C.LAYER_FILES  # dict: elevation, water_frac, rainfall, temperature, ndvi → filenames
```

### Thermal response (Mordecai 2013)

```python
C.T_OPT         # 25.0 °C — optimal temperature
C.T_HALF_WIDTH  # 8.0 °C — half-width of parabolic response
C.temp_suitability(T)   # → [0, 1] parabolic thermal suitability
C.mortality_rate(T)     # → per-step mortality (0.05 at 25 °C, rising outside viable range)
```

### Suitability weights

```python
C.WEIGHTS  # dict: water_frac=0.35, rainfall=0.20, temperature=0.20, ndvi=0.15, elevation=0.10
# Sum is asserted == 1.0
```

### Simulator v1 parameters

| Constant | Default | Description |
|---|---|---|
| `K_MAX` | 1000.0 | Carrying capacity |
| `WATER_THRESH` | 0.10 | Water fraction threshold |
| `MU` | 0.20 | Mortality rate |
| `R_MAX` | 0.30 | Max growth rate |
| `N_STEPS` | 60 | Simulation steps |
| `T_SNAP` | 5 | Snapshot interval |
| `SEED_DENSITY_FRAC` | 0.1 | Initial seed density fraction |

```python
C.SimParams          # dataclass with r_of(T) method
C.PARAM_RANGES      # randomization ranges for training rollouts
```

### U-Net / training

| Constant | Default | Description |
|---|---|---|
| `PATCH` | 64 | U-Net input patch size |
| `STRIDE` | 48 | U-Net stride |
| `UNET_CHANNELS` | (8, 16, 32, 64) | Channel dimensions |
| `LOSS_DICE_WEIGHT` | 1.0 | Dice loss weight |
| `LOSS_DICE_TAU` | 0.05 | Dice temperature |
| `PRESENCE_THRESH` | 0.05 | Presence threshold |
| `TRAIN_EPOCHS` | 8 | Training epochs |
| `TRAIN_LR` | 1e-3 | Learning rate |
| `TRAIN_BATCH` | 32 | Batch size |
| `N_ROLLOUTS` | 20 | Number of rollouts |
| `VAL_SPLIT_LON` | -1.0 | Validation split longitude |

### Validation

| Constant | Default |
|---|---|
| `AUC_N_BACKGROUND` | 10,000 |
| `AUC_BOOTSTRAP` | 1000 |
| `AUC_CI_TARGET` | 0.65 |
| `DICE_TARGET` | 0.60 |

---

## AOI — Area of Interest

```python
from mal_commonlib import AOI, Scale
# or
from mal_commonlib.aoi import AOI, Scale
```

Region-agnostic schema. Carries slug, name, bbox, CRS, resolution, scale, and optional GADM id. Consumed by data loaders and ABM.

### Scale enum

```python
class Scale(str, Enum):
    REGIONAL = "regional"        # 1 km grid, raw raster
    NATIONAL = "national"        # GADM-2 mean-pool
    CONTINENTAL = "continental"  # 5 km grid + GADM-0 mean-pool
```

### AOI constructor

```python
AOI(
    slug="ghana",               # [a-z0-9-], no leading/trailing/consecutive hyphens
    name="Ghana NMCP AOI",      # human-readable
    bbox=(-2.97, 4.69, 0.79, 9.79),  # (west, south, east, north)
    crs="EPSG:32630",           # parseable by pyproj
    resolution_m=1000,          # cell size in metres
    scale=Scale.REGIONAL,       # default
    gadm_id=None,               # optional GADM id
)
```

### Key properties

| Property | Returns |
|---|---|
| `crs_obj` | `pyproj.CRS` object |
| `width_m`, `height_m` | Dimensions in metres |
| `area_km2` | Area in km² |
| `geom` | `shapely.geometry.Polygon` bounding box |
| `cells_per_side()` | `(H, W)` cells at `resolution_m` |

### Class methods

```python
AOI.from_bbox(west, south, east, north, crs, slug, resolution_m, name=None, scale=Scale.REGIONAL)
AOI.from_gadm(gadm_id, crs, slug, resolution_m, gadm_path=None, name=None, scale=Scale.REGIONAL)
```

### I/O

```python
aoi.to_file(path)        # → Path (writes JSON)
AOI.from_file(path)      # → AOI (reads JSON)
```

### Conversion

```python
aoi.to_geoseries(crs=None)  # → gpd.GeoSeries
```

---

## Data loaders

All loaders share a common pattern:
1. Accept an `AOI` (bbox + CRS + resolution)
2. Download/cache source data
3. Reproject to the AOI's grid
4. Return `xr.DataArray` with dims `(y, x)`, dtype `float32`, CRS = `aoi.crs`, NoData = `-9999.0`

### Auth requirements

| Loader | Auth required | Env var / config |
|---|---|---|
| MERIT DEM | Yes (token) | `MERIT_AUTH_TOKEN`, `MERIT_DOWNLOAD_URL` (optional) |
| NASADEM (fallback) | No | — |
| CHIRPS | No | — |
| ERA5 | Yes (CDS) | `~/.cdsapirc` or `CDSAPI_URL`/`CDSAPI_KEY` |
| JRC GSW | No | — (Planetary Computer) |
| MODIS | Yes (token) | `EARTHDATA_TOKEN` |
| WorldCover | No | — (Planetary Computer) |

---

### DEM — `load_merit_dem`

```python
from mal_commonlib.data.loaders.dem import load_merit_dem

dem = load_merit_dem(aoi, cache_dir=None)
```

MERIT DEM 90 m (hydrologically conditioned, preferred for TWI). Falls back to NASADEM (30 m) when MERIT upstream is unreachable.

**Returns**: `xr.DataArray` (y, x), float32, metres, NoData = `-9999.0`

---

### CHIRPS — `load_chirps_rainfall`, `load_chirps_rainfall_daily`

```python
from mal_commonlib.data.loaders.chirps import load_chirps_rainfall, load_chirps_rainfall_daily

# Monthly total (mm)
rain = load_chirps_rainfall(aoi, year=2020, month=6, cache_dir=None)

# Daily (time, y, x) in mm/day
rain_daily = load_chirps_rainfall_daily(aoi, year=2020, month=6, cache_dir=None)
```

CHIRPS v2.0 daily 0.05° (~5 km), aggregated to monthly total. Returns raw mm (NOT normalized). The `rainfall_cap_mm` attr holds the P95 cap for documentation.

**Returns**: `xr.DataArray` (y, x), float32, mm/month, NoData = `-9999.0`

**Year range**: 1981+

---

### ERA5 — `load_era5_temp_suitability`, `load_era5_water_temp`, `sharpe_demichele_growth`

```python
from mal_commonlib.data.loaders.era5 import (
    load_era5_temp_suitability,
    load_era5_water_temp,
    sharpe_demichele_growth,
)

# Monthly temp_suitability [0, 1]
suit = load_era5_temp_suitability(aoi, year=2020, month=6, cache_dir=None)

# Daily temperature (time, y, x) in °C
temp_daily = load_era5_water_temp(aoi, year=2020, month=6, cache_dir=None)

# Standalone thermal response
s = sharpe_demichele_growth(T_celsius)  # → [0, 1]
```

ERA5-Land daily statistics `2m_temperature`, aggregated to monthly mean, then `sharpe_demichele_growth` applied: `s(T) = clip(1 - ((T - 25) / 8)², 0, 1)`.

**Returns**: `xr.DataArray` (y, x), float32, [0, 1], NoData = `-9999.0`

**Year range**: 1950+

**Auth**: CDS API credentials required (`~/.cdsapirc` or env vars).

---

### JRC GSW — `load_jrc_gsw_water_frac`

```python
from mal_commonlib.data.loaders.jrc_gsw import load_jrc_gsw_water_frac

water = load_jrc_gsw_water_frac(aoi, year=2021, month=None, cache_dir=None,
                                 water_classes=None, threshold_pct=80)
```

JRC Global Surface Water 30 m `occurrence` band via Planetary Computer STAC. Binarises at `threshold_pct=80` (standard "permanent water" per Pekel et al. 2016).

**Parameters**:
- `year`: 1984–2021 (default 2021). Falls back to 2020 if requested year unavailable.
- `month`: accepted for `build_env` signature uniformity; ignored.
- `threshold_pct`: 0–100, default 80.

**Returns**: `xr.DataArray` (y, x), float32, [0, 1], NoData = `-9999.0`

---

### MODIS — `load_modis_ndvi`

```python
from mal_commonlib.data.loaders.modis import load_modis_ndvi

ndvi = load_modis_ndvi(aoi, year=2020, month=6, cache_dir=None)
```

MODIS MOD13A3 v061 monthly NDVI 1 km. Rescaled from raw [-1, 1] to [0, 1] via `(ndvi + 1) / 2`. Uses `earthaccess` with `EARTHDATA_TOKEN`.

**Returns**: `xr.DataArray` (y, x), float32, [0, 1], NoData = `-9999.0`

**Auth**: `EARTHDATA_TOKEN` env var required.

---

### WorldCover — `load_worldcover_water_frac`

```python
from mal_commonlib.data.loaders.worldcover import load_worldcover_water_frac

water = load_worldcover_water_frac(aoi, year=2021, month=None, cache_dir=None,
                                    water_classes=None)
```

ESA WorldCover 10 m via Planetary Computer STAC. Default water classes: `(80, 90, 95)` — permanent water, herbaceous wetland, mangroves.

**Parameters**:
- `year`: 2020 or 2021.
- `month`: accepted for signature uniformity; ignored (annual product).
- `water_classes`: override default `(80, 90, 95)`.

**Returns**: `xr.DataArray` (y, x), float32, [0, 1], NoData = `-9999.0`

---

## Terrain — `compute_twi`

```python
from mal_commonlib.terrain.twi import compute_twi

twi = compute_twi(dem, cell_size_m=None)
```

Topographic Wetness Index: `TWI = ln(a / tan(β))` (Beven & Kirkby 1979). Pure numpy/scipy D8 flow-direction + flow-accumulation — no pysheds dependency.

**Parameters**:
- `dem`: `xr.DataArray` with dims `(y, x)`, values in metres.
- `cell_size_m`: pixel size. If None, inferred from `dem.rio.resolution()` or x/y coords.

**Returns**: `xr.DataArray` (y, x), float32, dimensionless, NoData = `-9999.0`

**Algorithm**: Central-difference slope → D8 flow direction (steepest descent) → topological-sort flow accumulation → TWI = ln(accumulated_cells × cell_size² / max(tan(β), ε))

---

## Data utils

```python
from mal_commonlib.data.utils import (
    read_raster,
    reproject_to_grid,
    points_to_grid,
    norm_minmax,
)
```

### `read_raster(path) → xr.DataArray`
Open a raster, mask nodata, return squeezed DataArray.

### `reproject_to_grid(src_path, ref, name) → np.ndarray`
Reproject raster to match reference grid. Applies nodata policy per layer name (`water_frac` → 0.0; others → AOI mean).

### `points_to_grid(lats, lons, affine, crs) → np.ndarray`
Map lon/lat points (EPSG:4326) to (row, col) in a UTM grid. Returns (N, 2) int array.

### `norm_minmax(a) → np.ndarray`
Min-max normalization to [0, 1].

---

## Common patterns

### Build an env tensor

```python
from mal_commonlib.aoi import AOI, Scale
from mal_commonlib.data.loaders.jrc_gsw import load_jrc_gsw_water_frac
from mal_commonlib.data.loaders.chirps import load_chirps_rainfall
from mal_commonlib.data.loaders.era5 import load_era5_temp_suitability
from mal_commonlib.data.loaders.modis import load_modis_ndvi

aoi = AOI.from_bbox(-2.97, 4.69, 0.79, 9.79, "EPSG:4326", "ghana", 1000)

water   = load_jrc_gsw_water_frac(aoi, year=2021)
rain    = load_chirps_rainfall(aoi, year=2020, month=6)
temp    = load_era5_temp_suitability(aoi, year=2020, month=6)
ndvi    = load_modis_ndvi(aoi, year=2020, month=6)

# Stack into (4, H, W) env tensor
import numpy as np
env = np.stack([water.values, rain.values, temp.values, ndvi.values], axis=0)
```

### Compute TWI from loaded DEM

```python
from mal_commonlib.data.loaders.dem import load_merit_dem
from mal_commonlib.terrain.twi import compute_twi

dem = load_merit_dem(aoi)
twi = compute_twi(dem)
```

### Save/load AOI to JSON

```python
aoi.to_file("aois/ghana.json")
restored = AOI.from_file("aois/ghana.json")
```

---

## NoData convention

Every loader and utility returns NoData as `-9999.0` (float32). The env tensor writer uses this sentinel consistently. Callers should replace `-9999.0` with `np.nan` before statistical operations, or mask with `arr == -9999.0`.
