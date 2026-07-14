"""MODIS MOD13A3 v061 monthly NDVI loader (M1.3a, env channel 3 — `ndvi`).

Public surface
--------------
``load_modis_ndvi(aoi, year, month, *, cache_dir=None) -> xr.DataArray``

The MOD13A3 product (MODIS/Terra Vegetation Indices Monthly L3 Global 1 km SIN
Grid, v061) is hosted by NASA LP DAAC and accessible via ``earthaccess``. We
search by ``short_name="MOD13A3", version="061"`` over a one-month temporal
window and bounding box covering the AOI, download the intersecting HDFs
(into ``cache_dir`` if provided), open with ``pyhdf`` (MOD13A3 is HDF4-EOS2)
and reproject the NDVI band from the 1 km sinusoidal grid to the AOI's grid.

HDF4 vs HDF5
------------
``rasterio``'s GDAL build on this platform does not include the HDF4 driver,
so ``rasterio.open()`` on a plain ``.hdf`` MOD13A3 file fails with
``RasterioIOError: .hdf not recognized``. We use ``pyhdf`` (the canonical
Python HDF4 reader, built on the HDF4 C library) instead. ``h5py`` is **not**
an option — it reads HDF5, which is a different file format despite the
similar name. (We keep ``h5py`` in the dep set because it is a useful
building block for other loaders, but the MOD13A3 reader does not use it.)

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
import re
import tempfile
from typing import Iterable

import numpy as np
import rasterio  # noqa: F401  (still used by the reproject step)
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

from mal_commonlib.aoi import AOI

# MOD13A3 fill value: -3000 in the raw int16 SDS. The original code assumed 0
# (which was a bug — 0 is a valid NDVI value). Fill cells are caught by the
# downstream ``arr < -0.2`` check in ``_rescale_ndvi`` because -3000 × 0.0001
# = -0.3 < -0.2. We still keep the explicit constant for documentation.
_FILL_RAW = -3000
_NODATA_OUT = np.float32(-9999.0)
_NODATA_OUT_SCALAR = -9999.0

# MODIS sinusoidal sphere radius (m). Used to convert the file's
# UpperLeftPointMtrs / LowerRightMtrs (in metres on the sinusoidal grid) to
# WGS-84 lat/lon.
_MODIS_SPHERE_RADIUS_M = 6371007.181


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


def _parse_modis_grid_extent(
    struct_metadata: str,
) -> tuple[float, float, float, float]:
    """Parse ``(x_ul, y_ul, x_lr, y_lr)`` in sinusoidal metres from a MODIS
    HDF-EOS2 ``StructMetadata.0`` block.

    Returns the upper-left and lower-right corners in metres on the MODIS
    sinusoidal grid (not lat/lon — use ``_sinusoidal_to_lonlat`` to convert).
    Raises ``ValueError`` if the block is missing or unparseable.
    """
    if not struct_metadata:
        raise ValueError("StructMetadata.0 is empty")
    ul = re.search(
        r"UpperLeftPointMtrs\s*=\s*\(\s*([-\d\.eE]+)\s*,\s*([-\d\.eE]+)\s*\)",
        struct_metadata,
    )
    lr = re.search(
        r"LowerRightMtrs\s*=\s*\(\s*([-\d\.eE]+)\s*,\s*([-\d\.eE]+)\s*\)",
        struct_metadata,
    )
    if not ul or not lr:
        raise ValueError(
            "StructMetadata.0 missing UpperLeftPointMtrs or LowerRightMtrs"
        )
    return (float(ul.group(1)), float(ul.group(2)), float(lr.group(1)), float(lr.group(2)))


def _sinusoidal_to_lonlat(x_m: float, y_m: float) -> tuple[float, float]:
    """Inverse GCTP_SNSOID (sinusoidal) for the standard parallel = 0.

    With ``R = 6371007.181 m`` (MODIS sphere), the forward mapping is
    ``x = R * lon_rad``, ``y = R * lat_rad``. The inverse is therefore
    trivial. Returns ``(lon_deg, lat_deg)`` — the WGS-84 degrees that the
    MODIS sinusoidal metres correspond to.

    Note: this used to return radians by mistake (loader bug discovered
    2026-07-14 via ``test_modis_ghana_smoke``); rasterio's ``from_bounds``
    and the downstream ``reproject_match`` both expect degrees, so a
    radians return value mapped MODIS pixels to ~(0, 0)° and produced
    an all-NaN grid for the Ghana AOI.
    """
    lon_rad = x_m / _MODIS_SPHERE_RADIUS_M
    lat_rad = y_m / _MODIS_SPHERE_RADIUS_M
    return (float(np.degrees(lon_rad)), float(np.degrees(lat_rad)))


def _ndvi_band_from_hdf(hdf_path: pathlib.Path) -> xr.DataArray:
    """Open a MOD13A3 HDF4 file and return the 1 km monthly NDVI band.

    Uses ``pyhdf.SD`` (HDF4) — see the module docstring for why ``h5py`` and
    ``rasterio`` are not used here. The MOD13A3 SDS is named ``1 km monthly
    NDVI`` with ``int16`` storage, fill ``-3000`` and a scale factor of
    ``0.0001`` (raw valid range ``[-2000, 10000]`` mapping to NDVI in
    ``[-0.2, 1.0]``). The grid bounding box is reconstructed from the file's
    ``StructMetadata.0`` ``UpperLeftPointMtrs`` / ``LowerRightMtrs`` using
    the inverse sinusoidal projection; we store the result in ``EPSG:4326``
    so the downstream ``reproject_match`` to the AOI's grid is straightforward.
    """
    from pyhdf.SD import SD, SDC  # imported lazily for a clear ModuleNotFoundError on import

    sd = SD(str(hdf_path), SDC.READ)
    try:
        # 1. Find the NDVI SDS. Try a few common naming conventions before
        #    falling back to a long_name search.
        sds_obj = None
        sds_name: str | None = None
        for candidate in ("1 km monthly NDVI", "NDVI"):
            if candidate in sd.datasets():
                sds_obj = sd.select(candidate)
                sds_name = candidate
                break
        if sds_obj is None:
            for name in sd.datasets():
                t = sd.select(name)
                ln = t.attributes().get("long_name", "")
                if "NDVI" in ln.upper() and "1 km" in ln.upper():
                    sds_obj = t
                    sds_name = name
                    break
                t.endaccess()
        if sds_obj is None:
            raise ValueError(
                f"No MOD13A3 NDVI SDS found in {hdf_path} "
                f"(datasets: {sorted(sd.datasets().keys())})"
            )
        try:
            arr_int16 = np.asarray(sds_obj[:], dtype=np.int16)
            sds_attrs = dict(sds_obj.attributes())
        finally:
            sds_obj.endaccess()

        # 2. Read StructMetadata.0 (top-level SD attribute) for the grid
        #    bounding box. Real MOD13A3 files expose the key as
        #    "StructMetadata.0"; some test fixtures / older tools use
        #    "StructMetadata_0" because dots are not valid Python identifiers.
        sd_attrs = sd.attributes()
        struct = sd_attrs.get("StructMetadata.0", "")
        if not struct:
            for k, v in sd_attrs.items():
                if k.replace(".", "_") == "StructMetadata_0":
                    struct = v
                    break
    finally:
        sd.end()

    # 3. Compute the geographic bounding box and the rasterio transform.
    x_ul, y_ul, x_lr, y_lr = _parse_modis_grid_extent(struct)
    west, north = _sinusoidal_to_lonlat(x_ul, y_ul)
    east, south = _sinusoidal_to_lonlat(x_lr, y_lr)
    h, w = arr_int16.shape
    transform = from_bounds(west, south, east, north, w, h)

    da = xr.DataArray(
        arr_int16,
        dims=("y", "x"),
        name="ndvi",
        attrs={
            "long_name": sds_attrs.get("long_name", "1 km monthly NDVI"),
            "source": "MOD13A3 v061",
            "units": "raw int16 (×0.0001 → NDVI in [-0.2, 1.0])",
            "fill_value": int(sds_attrs.get("_FillValue", _FILL_RAW)),
            "sds_name": sds_name,
        },
    )
    da.rio.write_crs("EPSG:4326", inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


def _rescale_ndvi(arr_raw: np.ndarray) -> np.ndarray:
    """Rescale MOD13A3 raw NDVI ∈ [-0.2, 1.0] to [0, 1]; emit -9999.0 for fill.

    The MOD13A3 SDS is stored as int16 in [-2000, 10000] corresponding to
    NDVI in [-0.2, 1.0]. If we get the raw int16 range we rescale by
    ``(raw * 0.0001)`` first to land in [-0.2, 1.0] then by ``(x + 1) / 2``
    to land in [0, 1]. If the values are already in [-1, 1] floats, we
    rescale directly.

    Fill handling: the MOD13A3 fill value is ``-3000`` (int16), which after
    the ``*0.0001`` rescale becomes ``-0.3``. The ``arr < -0.2`` mask below
    catches it (and any other out-of-range noise). We also keep an explicit
    check on ``_FILL_RAW`` for documentation.
    """
    arr = arr_raw.astype(np.float32)
    if np.nanmax(arr) > 1.5 or np.nanmin(arr) < -1.5:
        # Looks like raw int16 scale [-2000, 10000].
        arr = arr * np.float32(1e-4)
    # Fill: source fill is -3000 (catches as "out of range"). Treat NaN,
    # the explicit _FILL_RAW value, and any value outside [-0.2, 1.0] as
    # fill. The reproject step above may also produce NaN at the seams,
    # so we drop those here.
    fill_mask = (
        ~np.isfinite(arr)
        | (arr == np.float32(_FILL_RAW) * np.float32(1e-4))
        | (arr < -0.2)
        | (arr > 1.0)
    )
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

    The MODIS Sinusoidal grid extent is converted to WGS-84 lon/lat (in
    **degrees**) via ``_sinusoidal_to_lonlat`` before being fed to
    ``rasterio.transform.from_bounds`` and the AOI ``reproject_match``.
    The helper previously returned radians by mistake — see
    ``_sinusoidal_to_lonlat`` for the bug note (fixed 2026-07-14,
    GitHub issue #13).

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
