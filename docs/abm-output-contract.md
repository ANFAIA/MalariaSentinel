# ABM Output Contract — `arch-abm-output-contract` v1.0

**Date**: 2026-07-08 · **Version**: `v1.0` (`arch-abm-output-contract`) · **Status**: binding for M1.4 writer and M3-M4 U-Net reader.
**Source of truth**: design doc `~/.gstack/projects/ANFAIA-MalariaSentinel/davidflorezmazuera-main-design-20260708-120500.md`, node `arch-abm-output-contract` (line 122). This file is a codification of that node, not a redesign. Breaking the values below requires a new major version of the contract.

The thin-slice ABM (Mesa-Geo, M1) writes per-tick rasters and tensors. The U-Net surrogate (PyTorch, M3-M4) and the SDSS shell (M5-M6) read what the ABM writes. If the writer and reader disagree on shape, dtype, band order, normalization, CRS, or naming, the pipeline re-architectures. The contract pins every one of those values.

---

## §1 — State tensor

The state tensor is what the ABM produces per tick. One file per ABM tick.

| Property | Value |
|---|---|
| Shape | `(C=2, T, H, W)` |
| `dtype` | `float32` |
| Channel 0 | `density` — mosquitoes per cell, normalized `density / K_max` ∈ [0, 1] |
| Channel 1 | `suitability` — float32, ∈ [0, 1] |
| `K_max` (v1) | `1000` mosquitoes/cell (carried from the casablanca design; M2 calibrates against the 24 larval sites) |
| `T` (snapshot count) | Monthly snapshots — horizon is **monthly** for v1, matching the ABM's 30-day larval-cycle cadence (M1 decision; not per-experiment) |
| `H, W` | `H = W = 128` (see §4) |
| NoData (rasters) | `-9999.0` |
| NoData (masks) | `255` |
| File naming | `{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif` |
| Sidecar | same name + `.json` (see §3) |

`density` is written as the normalized channel (`density / K_max`). The denormalization is a scalar multiply at read time — the writer never stores raw counts in channel 0. `suitability` is the time-varying suitability field produced by the ABM at this tick; it is not the static env layer (see §2).

---

## §2 — Env tensor

The env tensor is the static context, one per `(aoi_slug, scale, year, month)`. It is deterministic per month — the data layer writes it once, the ABM reads it on every tick in that month.

| Property | Value |
|---|---|
| Shape | `(C_env=4, H, W)` |
| `dtype` | `float32` |
| Channel 0 | `water_frac` — ∈ [0, 1] by construction (fraction of cell covered by open water) |
| Channel 1 | `rainfall` — min-max normalized over the AOI's wet-season P95, clipped at the cap (mm/month) |
| Channel 2 | `temp_suitability` — ∈ [0, 1] by construction (Sharpe-DeMichele-style growth response) |
| Channel 3 | `ndvi` — rescaled to [0, 1] from the raw NDVI ∈ [−1, 1] |
| File naming | `{aoi_slug}_{scale}_{year}_{month:02d}_env.tif` (no seed — deterministic) |
| Sidecar | same name + `.json` (see §3) |

`water_frac` and `temp_suitability` are already in [0, 1] by construction — the writer does not rescale. `rainfall` and `ndvi` need explicit normalization; the writer is the only place that does it, and it writes the normalized values directly. Readers never re-normalize. The cap value for `rainfall` (the AOI's wet-season P95) lives in the sidecar (`rainfall_cap_mm`) so a reader can reconstruct the un-normalized value if needed.

---

## §3 — File format and naming

**Format**: GeoTIFF, Cloud-Optimized (COG-compatible). Internal tiling, overviews, and compression per the `rio cogeo validate` profile. One file per ABM tick (state) or per month (env). NoData tag is set in the GeoTIFF metadata (`-9999.0` for rasters, `255` for masks).

**State naming** (per ABM tick):
```
{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif
```
Example: `ghana-national_2km_2026_07_seed0042.tif`

**Env naming** (per month, deterministic):
```
{aoi_slug}_{scale}_{year}_{month:02d}_env.tif
```
Example: `ghana-national_2km_2026_07_env.tif`

**CRS**: must be `EPSG:4326` or a UTM zone (`EPSG:326xx` / `EPSG:327xx`). The thin slice uses `EPSG:4326` for v1. The writer **must** auto-reproject at write time if the source data is in a different CRS — silent reprojection is forbidden. The sidecar records the final CRS.

**Band descriptions in the COG** (set via `rasterio` `descriptions=[...]`):

| File | Band 0 | Band 1 | Band 2 | Band 3 |
|---|---|---|---|---|
| State | `density` | `suitability` | — | — |
| Env | `water_frac` | `rainfall` | `temp_suitability` | `ndvi` |

The U-Net reader **must** read by name, not by index, so adding a band later does not silently shift channels.

**Sidecar JSON** (same path as the `.tif`, suffix `.json`):
```json
{
  "crs": "EPSG:4326",
  "transform": [0.008333333333333, 0.0, -3.5, 0.0, -0.008333333333333, 12.0],
  "aoi_slug": "ghana-national",
  "scale": "2km",
  "year": 2026,
  "month": 7,
  "seed": 42,
  "generator_version": "m1-thin-0.1.0",
  "abm_params_hash": "sha256:8f3c1a2b4d5e6f70a1b2c3d4e5f60718293a4b5c6d7e8f90011223344556677"
}
```

Required keys: `crs`, `transform`, `aoi_slug`, `scale`, `year`, `month`, `seed` (state only — omit for env), `generator_version`, `abm_params_hash`. Optional but recommended: `rainfall_cap_mm` (env only), `k_max` (state only; defaults to `1000` if absent). The `transform` is the affine 6-tuple in `rasterio`-row-major order: `[a, b, c, d, e, f]` where `(a, b)` is the pixel size and `(c, f)` is the upper-left corner.

---

## §4 — Patch and tile rules

The U-Net input is `(C=2, T, H, W)` with `H = W = 128` (a fixed patch size — part of the architecture, not a choice the writer can make).

**AOI smaller than 128×128**: zero-pad the raster to `128×128` on the right and bottom edges. The padding cells are real `NoData` (`-9999.0` for rasters, `255` for masks); they are not zero. The sidecar's `transform` is unchanged — it still describes the AOI's upper-left corner and pixel size. The U-Net reader learns to ignore padded cells via the `NoData` mask.

**AOI larger than 128×128**: tile into non-overlapping `128×128` patches. Tile origin is the AOI's upper-left corner; tiles are emitted left-to-right, top-to-bottom. Each tile is a separate GeoTIFF with its own sidecar (the sidecar's `transform` reflects the tile's upper-left, not the AOI's). The convention is:

```
{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}_r{row:04d}_c{col:04d}.tif
```
Example: `ghana-national_2km_2026_07_seed0042_r0000_c0003.tif`

**How the U-Net reads tiles back**: the reader concatenates all tiles for a given `(year, month, seed)` along the row/column dimensions and applies a `1×1` convolution at the boundary in M3 (the U-Net does not see the tile seam in v1; a learned boundary fix is M7+). The full env tensor must be re-tiled with the same `(row, col)` indices as the state tiles — this is enforced by using a shared `tile_index.json` in the run directory.

---

## §5 — Versioning and stability

The contract is **`v1.0`**. Any change to the values in §1, §2, §3, or §4 — channel order, dtype, normalization rule, naming pattern, NoData sentinel, `K_max`, `H/W` — is a **breaking change** and requires a new major version (`v2.0`).

**Discovery**: the U-Net reader reads `arch-abm-output-contract` from the sidecar JSON's header (an additional optional key, e.g. `"contract": "arch-abm-output-contract@v1.0"`) to know which contract applies to a given file. If the key is absent, the reader falls back to `v1.0` and emits a warning. If the key is present and the major version is greater than the reader's `MAX_SUPPORTED_CONTRACT_VERSION`, the reader **must** refuse the file with a clear error — silent fallback is forbidden.

**Additive changes** (e.g. a new optional sidecar key, a new env channel at index 4) are **non-breaking** and bump the minor version (`v1.1`). The U-Net reader must ignore unknown sidecar keys and unknown band names.

The contract version is recorded in the sidecar under `"contract_version": "1.0"` (added in M1.4; readers must accept files with or without this key for the v1.0 → v1.1 transition).

---

## §6 — Reference implementation pointers

The contract is implemented in a single module — the candidate path is `mal-core/src/mal_core/output_contract.py` (lives in `mal-ghana-sim/src/mal_ghana_sim/output_contract.py` for the M1 thin slice, and is promoted to `mal-core/` once M2 validation passes). The module owns the channel-name constants, the sidecar schema, and the `rasterio.open(...)` / `da.write(...)` patterns below.

**Writer pattern** (M1.4, `mal-ghana-sim/src/mal_ghana_sim/abm/run.py`):
```python
import numpy as np
import rasterio
from rasterio.transform import Affine

def write_state_tick(path: str, density: np.ndarray, suitability: np.ndarray,
                     transform: Affine, crs: str = "EPSG:4326",
                     nodata: float = -9999.0) -> None:
    assert density.shape == suitability.shape, "channel shape mismatch"
    assert density.dtype == np.float32 and suitability.dtype == np.float32
    array = np.stack([density, suitability], axis=0)  # (C=2, H, W)
    profile = {
        "driver": "GTiff", "dtype": "float32", "count": 2,
        "height": array.shape[1], "width": array.shape[2],
        "crs": crs, "transform": transform, "nodata": nodata,
        "tiled": True, "compress": "deflate", "blockxsize": 128, "blockysize": 128,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array)
        dst.set_band_description(1, "density")
        dst.set_band_description(2, "suitability")
```

**Reader pattern** (M3-M4, `mal-ghana-sim/src/mal_ghana_sim/unet.py`):
```python
import rasterio

def read_state_by_name(path: str) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        names = src.descriptions
        density = src.read(names.index("density") + 1)        # band 1
        suitability = src.read(names.index("suitability") + 1)  # band 2
    return np.stack([density, suitability], axis=0), src.profile
```

The sidecar JSON is written with the same basename (`path.with_suffix(".tif").with_suffix(".json")` after the `.tif` is finalised). The full env tensor follows the same pattern with `count=4` and band descriptions `["water_frac", "rainfall", "temp_suitability", "ndvi"]`.
