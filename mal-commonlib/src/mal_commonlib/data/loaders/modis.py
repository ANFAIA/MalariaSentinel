"""MODIS MOD13A3 v061 monthly NDVI loader (M1.3a, env channel 3 — `ndvi`).

Public surface
--------------
``load_modis_ndvi(aoi, year, month, *, cache_dir=None) -> xr.DataArray``

The MOD13A3 product (MODIS/Terra Vegetation Indices Monthly L3 Global 1 km SIN
Grid, v061) is hosted by NASA LP DAAC and accessible via ``earthaccess``. We
search by ``short_name="MOD13A3", version="061"`` over a one-month temporal
window and bounding box covering the AOI, download the intersecting HDFs
(into ``cache_dir`` if provided), open with ``rasterio`` (MOD13A3 is HDF4)
and reproject the NDVI band from the 1 km sinusoidal grid to the AOI's grid.

Output contract (per ``docs/abm-output-contract.md`` §2, channel 3):
    * dims (y, x), dtype ``float32``
    * CRS = ``aoi.crs``
    * values in [0, 1] (rescaled from raw [-1, 1] via ``(ndvi + 1) / 2``)
    * NoData: ``-9999.0``

The function is structured so the heavy parts (network I/O, open/reproject of
the real MOD13A3 file) can be monkeypatched in tests. A "dry-run" path with
no network is achieved by monkeypatching ``earthaccess.search_data`` and
``earthaccess.download`` to return / yield synthetic file paths.
"""
from __future__ import annotations

import datetime as _dt
import os
import pathlib
import tempfile
from typing import Iterable

import numpy as np
import rasterio
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

from mal_commonlib.aoi import AOI

# MOD13A3 fill / out-of-range sentinel: the source uses 0 as "no data" for the
# NDVI SDS, with valid raw values in [-2000, 10000] scaled to [-0.2, 1.0]. We
# treat 0 (and any negative or NaN) as fill. The rescaled [0, 1] value of fill
# is -9999.0 in the output.
_FILL_RAW = 0
_NODATA_OUT = np.float32(-9999.0)
_NODATA_OUT_SCALAR = -9999.0


def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    if cache_dir is None:
        cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "mod13a3"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _search_window(year: int, month: int) -> tuple[str, str]:
    start = _dt.date(year, month, 1)
    if month == 12:
        end = _dt.date(year + 1, 1, 1) - _dt.timedelta(days=1)
    else:
        end = _dt.date(year, month + 1, 1) - _dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _aoi_bbox_for_earthaccess(aoi: AOI) -> tuple[float, float, float, float]:
    """Return (W, S, E, N) in WGS-84 for earthaccess.bounding_box=.

    earthaccess wants lon/lat regardless of the AOI's CRS, so we reproject
    the bbox if necessary.
    """
    import pyproj

    if str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
        w, s, e, n = aoi.bbox
    else:
        t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
        w, s, e, n = aoi.bbox
        w, s = t.transform(w, s)
        e, n = t.transform(e, n)
    return (float(w), float(s), float(e), float(n))


def _earthaccess_login() -> None:
    """Authenticate earthaccess via the EARTHDATA_TOKEN env var.

    earthaccess >=0.12 picks up ``EARTHDATA_TOKEN`` (a personal access token)
    automatically when ``login()`` is called. If the env var is absent or
    invalid, ``login()`` raises a clear error.
    """
    if not os.environ.get("EARTHDATA_TOKEN"):
        raise RuntimeError(
            "EARTHDATA_TOKEN env var is not set; the MOD13A3 loader needs it to "
            "authenticate against NASA Earthdata. Generate a token at "
            "https://urs.earthdata.nasa.gov/user_tokens and export it."
        )
    import earthaccess  # imported lazily so the module loads even if earthaccess is broken

    earthaccess.login()


def _ndvi_band_from_hdf(hdf_path: pathlib.Path) -> xr.DataArray:
    """Open a MOD13A3 HDF4 file and return the 1 km monthly NDVI band.

    MOD13A3 HDF4 subdataset names include ``HDF4_EOS:EOS_GRID:"<file>":MOD_Grid_monthly_1km_VI:1 km monthly NDVI``.
    We open with rasterio, identify the band matching the NDVI long name,
    and return a single-band ``xr.DataArray`` with CRS set.
    """
    with rasterio.open(hdf_path) as src:
        descriptions = list(src.descriptions or ())
        band_index = None
        for i, desc in enumerate(descriptions, start=1):
            if desc and "NDVI" in desc.upper() and "1 km" in desc:
                band_index = i
                break
        if band_index is None:
            for i, desc in enumerate(descriptions, start=1):
                if desc and "NDVI" in desc.upper():
                    band_index = i
                    break
        if band_index is None:
            band_index = 1
        raw = src.read(band_index)
        if hasattr(raw, "filled"):
            raw = np.ma.filled(raw, np.nan)
        # rasterio returns (count, H, W) — squeeze to (H, W) so the rest of
        # the pipeline is 2-D. Use np.asarray with copy=False to avoid the
        # numpy 2.5 "shape assignment" deprecation.
        arr = np.asarray(raw, dtype=np.float32)
        if arr.ndim == 3 and arr.shape[0] == 1:
            arr = arr.reshape(arr.shape[1], arr.shape[2])
        crs = src.crs
        transform = src.transform
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="ndvi",
        attrs={
            "long_name": "1 km monthly NDVI",
            "source": "MOD13A3 v061",
            "units": "raw [-1, 1]",
        },
    )
    da.rio.write_crs(crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


def _rescale_ndvi(arr_raw: np.ndarray) -> np.ndarray:
    """Rescale MOD13A3 raw NDVI ∈ [-1, 1] to [0, 1]; emit -9999.0 for fill.

    The MOD13A3 SDS is stored as int16 in [-2000, 10000] corresponding to
    NDVI in [-0.2, 1.0]. If we get the raw int16 range we rescale by
    ``(raw * 0.0001)`` first to land in [-0.2, 1.0] then by ``(x + 1) / 2``
    to land in [0, 1]. If the values are already in [-1, 1] floats, we
    rescale directly.
    """
    arr = arr_raw.astype(np.float32)
    if np.nanmax(arr) > 1.5 or np.nanmin(arr) < -1.5:
        # Looks like raw int16 scale [-2000, 10000].
        arr = arr * np.float32(1e-4)
    # Fill: source fill is 0; also treat NaN, out-of-range as fill.
    fill_mask = ~np.isfinite(arr) | (arr == _FILL_RAW) | (arr < -0.2) | (arr > 1.0)
    out = (arr + np.float32(1.0)) / np.float32(2.0)
    out = np.clip(out, np.float32(0.0), np.float32(1.0))
    out = np.where(fill_mask, _NODATA_OUT, out).astype(np.float32)
    return out


def _make_reference_grid(aoi: AOI) -> xr.DataArray:
    """Return a 1-cell-band reference DataArray covering the AOI in ``aoi.crs``."""
    h, w = aoi.cells_per_side()
    wmin, smin, wmax, smax = aoi.bbox
    transform = from_bounds(wmin, smin, wmax, smax, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"), name="ref")
    da.rio.write_crs(aoi.crs, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


def _merge_and_reproject(
    ndvi_bands: Iterable[xr.DataArray], aoi: AOI
) -> xr.DataArray:
    """Reproject each MOD13A3 tile to the AOI's grid and mean-combine valid pixels.

    Each tile is reprojected independently to the AOI reference grid; the
    resampled arrays are then combined by taking the mean of the valid (non
    nodata) pixels. Cells where every tile is nodata stay ``-9999.0``.
    """
    bands = list(ndvi_bands)
    if not bands:
        raise ValueError("ndvi_bands is empty")
    ref = _make_reference_grid(aoi)
    # Stack all reprojected tiles, then mean across the stack with nodata masking.
    reprojected = []
    for b in bands:
        # First rescale the raw band to [-1, 1] floats (in source CRS).
        arr_pre = b.values.astype(np.float32)
        if np.nanmax(arr_pre) > 1.5 or np.nanmin(arr_pre) < -1.5:
            arr_pre = arr_pre * np.float32(1e-4)
        b_pre = xr.DataArray(arr_pre, dims=("y", "x"), name="ndvi")
        b_pre.rio.write_crs(b.rio.crs, inplace=True)
        b_pre.rio.write_transform(b.rio.transform(), inplace=True)
        # Reproject to the AOI's grid (bilinear for the continuous NDVI).
        rep = b_pre.rio.reproject_match(ref, resampling=Resampling.bilinear)
        reprojected.append(rep.values.astype(np.float32))

    stack = np.stack(reprojected, axis=0)  # (N, H, W)
    # Treat values outside [-0.2, 1.0] (i.e. fill) as nodata.
    valid = (stack >= -0.2) & (stack <= 1.0) & np.isfinite(stack)
    with np.errstate(invalid="ignore"):
        out = np.where(valid.any(axis=0), np.nanmean(np.where(valid, stack, np.nan), axis=0), np.nan)
    return _rescale_ndvi(out)


def load_modis_ndvi(
    aoi: AOI,
    year: int,
    month: int,
    *,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load MODIS MOD13A3 v061 monthly NDVI for the AOI (env channel 3 — ``ndvi``).

    Uses earthaccess to authenticate via the ``EARTHDATA_TOKEN`` env var and
    download the MOD13A3 tile(s) that intersect the AOI. The 1 km NDVI is
    rescaled from the raw [-1, 1] to [0, 1] for the env tensor.

    Args:
        aoi: the AOI.
        year, month: 1-indexed month.
        cache_dir: optional local cache for downloaded HDFs. If absent, a temp
            directory under the system temp dir is used.

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, CRS = ``aoi.crs``.
        Values in [0, 1]. ``-9999.0`` for NoData.
    """
    _earthaccess_login()
    import earthaccess

    cache = _ensure_cache_dir(cache_dir)
    start, end = _search_window(year, month)
    bbox = _aoi_bbox_for_earthaccess(aoi)

    results = earthaccess.search_data(
        short_name="MOD13A3",
        version="061",
        temporal=(start, end),
        bounding_box=bbox,
    )
    if not results:
        raise FileNotFoundError(
            f"No MOD13A3 v061 granules found for {aoi.slug} {year}-{month:02d} "
            f"(bbox={bbox}, window={start}..{end})"
        )
    paths = earthaccess.download(results, local_path=str(cache))
    flat_paths: list[pathlib.Path] = []
    for p in paths:
        if isinstance(p, (list, tuple)):
            flat_paths.extend(pathlib.Path(x) for x in p)
        else:
            flat_paths.append(pathlib.Path(p))

    ndvi_bands = [_ndvi_band_from_hdf(p) for p in flat_paths]
    arr = _merge_and_reproject(ndvi_bands, aoi)

    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)
    out = xr.DataArray(
        arr,
        dims=("y", "x"),
        name="ndvi",
        attrs={
            "long_name": "1 km monthly NDVI (rescaled)",
            "source": "MOD13A3 v061",
            "units": "unitless [0, 1]",
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    out.rio.write_crs(aoi.crs, inplace=True)
    out.rio.write_transform(transform, inplace=True)
    out.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return out


__all__ = ["load_modis_ndvi", "NODATA_OUT"]
NODATA_OUT = _NODATA_OUT_SCALAR
