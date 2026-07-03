"""Stage 1 — data ingestion.

Builds a common 1 km EPSG:32630 grid from the SRTM DEM, reprojects+resamples every
environmental layer onto it (per-layer nodata policy), and stacks them into a single
(C, H, W) float32 array cached to runs/env_stack.npz.

SRTM elevation is local (have it). The other four layers (water_frac, rainfall,
temperature, ndvi) are downloaded on first use into runs/layers/. Download helpers
are implemented but only exercised when you run build_stack(download=True).
"""
from __future__ import annotations

import io
import pathlib
import urllib.request
import zipfile

import numpy as np
import rasterio
import rioxarray  # noqa: F401  (registers .rio on xarray)
import xarray as xr
from rasterio.transform import array_bounds

from . import config as C

LAYER_ORDER = ["elevation", "water_frac", "rainfall", "temperature", "ndvi"]


# --------------------------------------------------------------------------
# Reference grid (from SRTM, the only layer we already have on disk)
# --------------------------------------------------------------------------
def _open_1km_elevation() -> xr.DataArray:
    """Load SRTM, mask nodata, reproject to EPSG:32630 @1 km. Returns the reference grid."""
    da = xr.open_dataarray(C.SRTM_DEM, engine="rasterio").squeeze(drop=True)
    if da.rio.nodata is not None:
        da = da.where(da != da.rio.nodata)
    da = da.rio.write_nodata(np.nan)
    ref = da.rio.reproject(
        C.DST_CRS,
        resolution=C.DST_RES,
        resampling=rasterio.enums.Resampling.average,
    )
    ref = ref.rio.write_nodata(np.nan)
    ref.name = "elevation"
    return ref


def reference_grid() -> xr.DataArray:
    """The 1 km UTM grid (template for all layers). Cached under runs/layers/."""
    cache = C.LAYER_DIR / "elevation_1km.tif"
    if cache.exists():
        return xr.open_dataarray(cache, engine="rasterio").squeeze(drop=True)
    ref = _open_1km_elevation()
    ref.rio.to_raster(cache)
    return ref


# --------------------------------------------------------------------------
# Layer reproject + nodata policy
# --------------------------------------------------------------------------
NODATA_POLICY = {
    "water_frac":  0.0,           # land
    "rainfall":    "aoi_mean",
    "temperature": "aoi_mean",
    "ndvi":        "aoi_mean",
    "elevation":   "aoi_mean",
}


def _reproject_layer(name: str, path: pathlib.Path, ref: xr.DataArray) -> np.ndarray:
    da = xr.open_dataarray(path, engine="rasterio").squeeze(drop=True)
    if da.rio.nodata is not None:
        da = da.where(da != da.rio.nodata)
    da = da.rio.write_nodata(np.nan)
    # resample: continuous -> mean; water handled as binary->mean before reaching here
    rep = da.rio.reproject_match(ref, resampling=rasterio.enums.Resampling.average)
    arr = rep.to_numpy().astype(np.float32)
    policy = NODATA_POLICY[name]
    nan_mask = ~np.isfinite(arr)
    if nan_mask.any():
        if policy == "aoi_mean":
            fill = float(np.nanmean(arr)) if np.isfinite(arr).any() else 0.0
        else:
            fill = float(policy)
        arr = np.where(nan_mask, fill, arr)
    return arr


# --------------------------------------------------------------------------
# Download helpers (free, no cloud-compute; MODIS uses public fallback)
# --------------------------------------------------------------------------
WORLDCLIM_BIO_ZIP = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_5m_bio.zip"
# CHIRPSclim dropped: rainfall now comes from WorldClim BIO12 (same climatological-normal
# character; one fewer download). CHIRPS upgrade is a v2 option if sub-monthly rainfall is needed.
# Note: using 5min (~9km) bioclim, not 2.5min, to keep the zip ~150MB vs 658MB. Fine for a smooth
# climatology over the Ghana AOI; resampled (smoothed) to the 1 km grid.
JRC_GSW_TILES = [
    # occurrence band; 10x10 deg tiles, named by UPPER-LEFT corner. AOI lat 4.7-9.8 -> tile
    # with top edge at 10 ("10N"); lon straddles 0 -> "10W" (covers -10..0) + "0E" (covers 0..10).
    "https://storage.googleapis.com/global-surface-water/downloads/occurrence/occurrence_10W_10N.tif",
    "https://storage.googleapis.com/global-surface-water/downloads/occurrence/occurrence_0E_10N.tif",
]


def _download(url: str, dest: pathlib.Path, timeout: int = 600) -> pathlib.Path:
    if dest.exists() and dest.stat().st_size > 1024:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}\n  -> {dest}")
    urllib.request.urlretrieve(url, dest)
    return dest


def fetch_worldclim_bioclim() -> tuple[pathlib.Path, pathlib.Path]:
    """WorldClim 2.1 bioclim 2.5min. Extract BIO1 (annual mean temp, deg C) and BIO12 (annual precip, mm)."""
    dest = C.LAYER_DIR / "wc2.1_5m_bio.zip"
    bio1 = C.LAYER_DIR / "wc2.1_5m_bio_1.tif"
    bio12 = C.LAYER_DIR / "wc2.1_5m_bio_12.tif"
    if bio1.exists() and bio12.exists():
        return bio1, bio12
    _download(WORLDCLIM_BIO_ZIP, dest)
    with zipfile.ZipFile(dest) as z:
        names = z.namelist()
        m1 = next(n for n in names if n.endswith("bio_1.tif"))
        m12 = next(n for n in names if n.endswith("bio_12.tif"))
        z.extract(m1, C.LAYER_DIR); (C.LAYER_DIR / m1).rename(bio1)
        z.extract(m12, C.LAYER_DIR); (C.LAYER_DIR / m12).rename(bio12)
    return bio1, bio12


def fetch_jrc_water(ref: xr.DataArray) -> pathlib.Path:
    """JRC Global Surface Water occurrence -> binary water mask (>=10) -> fraction at 1 km.

    The AOI straddles two adjacent 10x10 deg tiles and is much smaller than a tile, so we
    read only the AOI window from each tile (via rasterio windows), threshold to binary,
    and reproject-average onto the ref grid — never loading a full ~40000x40000 tile.
    """
    from rasterio import windows
    from rasterio.warp import reproject, Resampling

    out = C.LAYER_DIR / "water_frac_1km.tif"
    if out.exists():
        return out
    tiles = [_download(u, C.LAYER_DIR / pathlib.Path(u).name) for u in JRC_GSW_TILES]
    H, W = ref.rio.height, ref.rio.width
    dst_transform = ref.rio.transform()
    acc = np.zeros((H, W), dtype=np.float32)
    for t in tiles:
        with rasterio.open(t) as src:
            # clip the AOI bbox to this tile's own bounds, in source (EPSG:4326) coords
            tb = src.bounds
            w0, e0 = max(C.AOI_W, tb.left), min(C.AOI_E, tb.right)
            s0, n0 = max(C.AOI_S, tb.bottom), min(C.AOI_N, tb.top)
            if w0 >= e0 or s0 >= n0:
                continue  # tile doesn't overlap the AOI
            win = windows.from_bounds(w0, s0, e0, n0, src.transform)
            data = src.read(1, window=win).astype("float32")
            nodata = src.nodata if src.nodata is not None else -1
            data = np.where(data == nodata, np.nan, data)
            win_transform = src.window_transform(win)
        binary = (data >= 10).astype("float32")        # 1 = water present >=10% of years
        binary = np.where(~np.isfinite(data), 0.0, binary)
        dst = np.zeros((H, W), dtype=np.float32)
        reproject(
            binary, dst,
            src_transform=win_transform, src_crs=src.crs,
            dst_transform=dst_transform, dst_crs=C.DST_CRS,
            resampling=Resampling.average, src_nodata=0.0,
        )
        acc = np.fmax(acc, dst)
    with rasterio.open(
        out, "w", driver="GTiff", height=H, width=W, count=1, dtype="float32",
        crs=ref.rio.crs, transform=dst_transform,
    ) as dst_:
        dst_.write(acc.astype("float32"), 1)
    return out


def fetch_modis_ndvi() -> pathlib.Path | None:
    """MODIS MOD13A2 NDVI multi-year annual mean.

    Public fallback (no NASA Earthdata login): download a static NDVI climatology
    if a public mirror is configured; otherwise return None and we proceed without
    NDVI (its 0.15 weight is redistributed). AppEEARS path needs Earthdata creds.
    """
    # TODO(M2): wire a public NDVI source or accept Earthdata creds for AppEEARS.
    print("  [ndvi] no public source wired yet; proceeding without NDVI (weight redistributed).")
    return None


# --------------------------------------------------------------------------
# Stack assembly
# --------------------------------------------------------------------------
def build_stack(download: bool = False) -> tuple[np.ndarray, dict]:
    """Return (env_stack[C,H,W], meta). meta has affine/crs/layer_order."""
    ref = reference_grid()
    H, W = ref.rio.height, ref.rio.width
    affine = ref.rio.transform()
    crs = ref.rio.crs.to_string() if ref.rio.crs else C.DST_CRS

    sources = {
        "elevation": C.LAYER_DIR / "elevation_1km.tif",
        "water_frac": C.LAYER_DIR / "water_frac_1km.tif",
        "rainfall": C.LAYER_DIR / "rainfall_1km.tif",
        "temperature": C.LAYER_DIR / "temperature_1km.tif",
        "ndvi": C.LAYER_DIR / "ndvi_1km.tif",
    }
    if download:
        # elevation reference grid materialised
        if not (C.LAYER_DIR / "elevation_1km.tif").exists():
            ref.rio.to_raster(C.LAYER_DIR / "elevation_1km.tif")
        # WorldClim BIO1 (temp) + BIO12 (rainfall) from one zip
        bio1, bio12 = fetch_worldclim_bioclim()
        if not sources["temperature"].exists():
            _reproject_to_1km(bio1, "temperature", ref)
        if not sources["rainfall"].exists():
            _reproject_to_1km(bio12, "rainfall", ref)
        # JRC surface water (thresholds + reprojects internally)
        fetch_jrc_water(ref)
        # MODIS NDVI: needs NASA Earthdata login (see fetch_modis_ndvi). v1 runs without it.
        ndvi = fetch_modis_ndvi()
        if ndvi is not None and not sources["ndvi"].exists():
            _reproject_to_1km(ndvi, "ndvi", ref)

    stack = np.full((len(LAYER_ORDER), H, W), np.nan, dtype=np.float32)
    present = []
    for i, name in enumerate(LAYER_ORDER):
        p = sources[name]
        if not p.exists():
            print(f"  [{name}] missing; skipping (will redistribute weight at suitability).")
            continue
        stack[i] = _reproject_layer(name, p, ref)
        present.append(name)

    meta = dict(affine=affine, crs=crs, height=H, width=W, order=LAYER_ORDER, present=present)
    np.savez_compressed(C.STACK_CACHE, stack=stack, **{k: np.array(v) for k, v in meta.items() if not isinstance(v, tuple)})
    # affine is an Affine (tuple-like) -> save as array
    print(f"stack {stack.shape} cached -> {C.STACK_CACHE}  present={present}")
    return stack, meta


def _reproject_to_1km(src_path: pathlib.Path, name: str, ref: xr.DataArray) -> None:
    arr = _reproject_layer(name, src_path, ref)
    out = C.LAYER_DIR / f"{name}_1km.tif"
    with rasterio.open(
        out, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
        count=1, dtype="float32", crs=C.DST_CRS, transform=ref.rio.transform(),
    ) as dst:
        dst.write(arr, 1)
