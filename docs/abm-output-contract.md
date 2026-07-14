# ABM Output Contract — `arch-abm-output-contract` v1.0

**Date**: 2026-07-08 · **Version**: `v1.0` (`arch-abm-output-contract`) · **Status**: binding for M1.4 writer and M3-M4 U-Net reader.
**Source of truth**: design doc `~/.gstack/projects/ANFAIA-MalariaSentinel/davidflorezmazuera-main-design-20260708-120500.md`, node `arch-abm-output-contract` (line 122). This file is a codification of that node, not a redesign. Breaking the values below requires a new major version of the contract.

The thin-slice ABM (Mesa-Geo, M1) writes per-tick rasters and tensors. The U-Net surrogate (PyTorch, M3-M4) and the SDSS shell (M5-M6) read what the ABM writes. If the writer and reader disagree on shape, dtype, band order, normalization, CRS, or naming, the pipeline re-architectures. The contract pins every one of those values.

> **M2 patch (2026-07-13, channel 1 semantics only):** v1 of this contract
> defined channel 1 (`suitability`) as "1.0 for cells with an active
> patch, else 0.0". The M2 real-data validation ran on the 20 larval
> sites in `data/ghana_idit/occurrence.txt` and observed that those
> sites sit in dry cells within dispersal range of water — the
> active-patch semantics gave them `suitability = 0`, so the AUC was
> NaN. The M2 fix (commits in the `m2-combined` branch) keeps the
> **same** contract version, dtype, shape, CRS, and `band_names` array
> but switches channel 1 to the **adult mosquito density per cell**
> (`n_adults / K_max`, ∈ [0, 1]). The U-Net reader in M3-M4 reads by
> band name (not by index), so the reader does not need to know which
> "version" produced a given file — the band description is the
> contract. Shape, dtype, CRS, NoData, and naming are unchanged; only
> the *meaning* of the value in band 1 changed. Future contract
> changes that touch any of the values in §1, §2, §3, or §4 still
> require a new major version.

---

## §1 — State tensor

The state tensor is what the ABM produces per tick. One file per ABM tick.

| Property | Value |
|---|---|
| Shape | `(C=2, T, H, W)` |
| `dtype` | `float32` |
| Channel 0 | `density` — mosquitoes per cell, normalized `density / K_max` ∈ [0, 1] (larvae + adults; v1+v2) |
| Channel 1 | `suitability` — float32, ∈ [0, 1]. v1: 1.0 for cells with an active patch, else 0.0. **v2 (M2 fix):** `n_adults / K_max` per cell (adult density only, not larvae). **v2.1 (M2 combined, C1):** the cell is computed from each adult's current `lon/lat` (post-dispersal), snapped to the AOI grid via `rasterio.transform.rowcol`; adults outside the AOI clamp to the nearest edge cell. |
| `K_max` (v1) | `1000` mosquitoes/cell (carried from the casablanca design; M2 calibrates against the 24 larval sites) |
| `T` (snapshot count) | Monthly snapshots — horizon is **monthly** for v1, matching the ABM's 30-day larval-cycle cadence (M1 decision; not per-experiment) |
| `H, W` | `H = W = 128` (see §4) |
| NoData (rasters) | `-9999.0` |
| NoData (masks) | `255` |
| File naming | `{aoi_slug}_{scale}_{year}_{month:02d}_seed{seed:04d}.tif` |
| Sidecar | same name + `.json` (see §3) |

`density` is written as the normalized channel (`density / K_max`). The denormalization is a scalar multiply at read time — the writer never stores raw counts in channel 0.

**Channel 1 (`suitability`) — v1 vs v2 (M2 fix):** v1 was the binary
"active-patch" map (1.0 at cells where the climate engine activated a
habitat patch on this day, 0.0 elsewhere). v2 is the per-cell adult
density (`n_adults / K_max` ∈ [0, 1]). The biology says a female adult
at a site (after dispersal from a water cell) seeks nearby water to
lay eggs, so the suitability for *occupancy* is best modelled by
adult presence, not by whether the cell itself is a habitat patch.
The v2 switch lets the 20 M2 larval sites (which sit in dry cells
near water) report non-zero suitability from the adults that
dispersed there. The M1.5 ``coordinator.suitability_grid`` keeps the
v1 path as a backward-compat fallback when called with no
``mosquito_df`` argument; the M2 facade always passes the submodel's
``df`` and therefore always writes the v2 band.

**Channel 1 (`suitability`) — v2.1 (M2 combined, C1, post-dispersal):**
v2 grouped adults by their `patch_id` (the patch they were born
into). But ``_adult_dispersal`` moves adults' ``lon/lat`` by a clipped
Gaussian kernel; their `patch_id` (and `row`, `col`) is **not** updated.
The v1 ``adult_density_by_patch`` therefore reports the adult at its
origin patch's cell, even after the adult has moved to a different
cell. The 20 M2 larval sites in `data/ghana_idit/occurrence.txt` are
dry cells within ``An. gambiae`` s.s. dispersal range of water — the
adults that emerged from a water cell and dispersed into a dry site
cell are missed by `adult_density_by_patch`. v2.1 introduces
``MosquitoSubmodel.adult_density_by_cell(aoi)``, which uses each
adult's **current** ``lon/lat`` (post-dispersal) and snaps it onto the
AOI grid via ``rasterio.transform.rowcol``. The
``coordinator.suitability_grid`` v2 path calls this method when both
``mosquito_df`` and ``submodel`` are passed. The v1 binary map and
the v2 ``patch_id``-grouped path are kept as backward-compat
fallbacks; the M2 facade always writes the v2.1 band.

**C2 (M2 combined, dynamic patches):** the per-patch state exchanged
with the submodel is now the **union** of pre-existing patches
(loaded from the gpkg) and dynamic patches (cells where the
PLUVIAL_POOL rule holds today: `TWI > 8 AND water_frac > 0 AND
rain_24h > 15mm`). Dynamic patches are assigned stable `patch_id`s
on first emergence and retained in the registry (site fidelity);
they reappear in the patch-state DataFrame automatically if the rule
holds again on a later day. The contract version stays `1.0`.

---

## §2 — Env tensor

The env tensor is the static context, one per `(aoi_slug, scale, year, month)`. It is deterministic per month — the data layer writes it once, the ABM reads it on every tick in that month.

| Property | Value |
|---|---|
| Shape | `(C_env=4, H, W)` |
| `dtype` | `float32` |
| Channel 0 | `water_frac` — ∈ [0, 1] by construction (fraction of cell covered by open water) |
| Channel 1 | `rainfall` — raw monthly total in mm (the suitability overlay applies its own min-max normalization at consumption time) |
| Channel 2 | `temp_suitability` — ∈ [0, 1] by construction (Sharpe-DeMichele-style growth response) |
| Channel 3 | `ndvi` — rescaled to [0, 1] from the raw NDVI ∈ [−1, 1] |
| File naming | `{aoi_slug}_{scale}_{year}_{month:02d}_env.tif` (no seed — deterministic) |
| Sidecar | same name + `.json` (see §3) |

`water_frac` and `temp_suitability` are already in [0, 1] by construction — the writer does not rescale. `ndvi` is rescaled at write time and the writer is the only place that does it. `rainfall` is the **raw** monthly total in mm (e.g. 50–300 mm for Ghana's wet season); the ABM compares the band against `RAIN_THRESHOLD_MM = 15` to activate habitat patches, so a P95-normalized band would never cross the threshold and break the activation rule. The suitability overlay (`suitability_from_stack`) re-normalizes rainfall on consumption via its own min-max — the env band must therefore be raw mm, not [0, 1]. The P95 cap used by the (now-removed) writer-side normalization is still computed and lives in the sidecar as `rainfall_cap_mm` for documentation.

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
