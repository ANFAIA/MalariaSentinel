"""Shared data utilities: raster I/O, reprojection, point-to-grid mapping."""
from __future__ import annotations

import pathlib

import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr

from mal_commonlib import config as C


def read_raster(path: pathlib.Path) -> xr.DataArray:
    """Open a raster, mask nodata, return a squeezed DataArray."""
    da = xr.open_dataarray(path, engine="rasterio").squeeze(drop=True)
    if da.rio.nodata is not None:
        da = da.where(da != da.rio.nodata)
    return da.rio.write_nodata(np.nan)


def reproject_to_grid(
    src_path: pathlib.Path,
    ref: xr.DataArray,
    name: str = "layer",
) -> np.ndarray:
    """Reproject a raster to match the reference grid, applying nodata policy."""
    da = xr.open_dataarray(src_path, engine="rasterio").squeeze(drop=True)
    if da.rio.nodata is not None:
        da = da.where(da != da.rio.nodata)
    da = da.rio.write_nodata(np.nan)
    rep = da.rio.reproject_match(ref, resampling=rasterio.enums.Resampling.average)
    arr = rep.to_numpy().astype(np.float32)

    policy = _nodata_policy(name)
    nan_mask = ~np.isfinite(arr)
    if nan_mask.any():
        if policy == "aoi_mean":
            fill = float(np.nanmean(arr)) if np.isfinite(arr).any() else 0.0
        else:
            fill = float(policy)
        arr = np.where(nan_mask, fill, arr)
    return arr


def _nodata_policy(name: str) -> str | float:
    return {
        "water_frac":  0.0,
        "rainfall":    "aoi_mean",
        "temperature": "aoi_mean",
        "ndvi":        "aoi_mean",
        "elevation":   "aoi_mean",
    }.get(name, "aoi_mean")


def points_to_grid(lats, lons, affine, crs=C.DST_CRS) -> np.ndarray:
    """Map lon/lat occurrence points (EPSG:4326) to grid (row,col) in a UTM grid."""
    from pyproj import Transformer
    from rasterio.transform import rowcol
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = t.transform(lons, lats)
    rows, cols = rowcol(affine, xs, ys)
    return np.stack([np.asarray(rows), np.asarray(cols)], axis=1)


def norm_minmax(a: np.ndarray) -> np.ndarray:
    """Min-max normalization to [0,1]."""
    lo = float(np.nanmin(a)); hi = float(np.nanmax(a))
    if hi - lo < 1e-9:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0, 1)