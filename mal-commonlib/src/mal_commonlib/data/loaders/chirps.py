"""CHIRPS v2.0 daily precipitation loader (M1.3a, channel: rainfall).

Public surface:
    load_chirps_rainfall(aoi, year, month, *, cache_dir=None) -> xr.DataArray

Source: UCSB Climate Hazards Center CHIRPS v2.0 (public, no auth).
Format: daily gzipped GeoTIFFs at 0.05° (~5 km) resolution; one file per day.
URL pattern: https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/<YYYY>/chirps-v2.0.<YYYY>.<MM>.<DD>.tif.gz

Notes:
    * CHIRPS also publishes per-month NetCDF-4 files at
      https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p05/by_month/...
      but reading those requires ``netCDF4`` or ``h5netcdf``, neither of which
      is a project dependency. v1 therefore uses the daily GeoTIFFs, which
      are readable with the already-installed ``rasterio`` / ``rioxarray``.
    * Returns raw mm (monthly total precipitation), NOT a P95-normalized
      value. The ABM compares the env band against
      ``RAIN_THRESHOLD_MM = 15`` to activate habitat patches, so the band
      must be in mm. The suitability overlay in
      ``mal-ghana-sim/src/mal_ghana_sim/suitability.py`` applies its own
      min-max normalization at consumption time — a previous version of
      this loader normalized the band in [0, 1] here, which both broke the
      ABM's threshold check and was redundant with the overlay's
      normalization. The helper ``_normalize_rainfall`` is retained (and
      still used to compute the wet-season P95 cap for the sidecar /
      ``rainfall_cap_mm`` attr) but is no longer applied to the band.
    * This loader only emits a single channel (``rainfall``); the M1.3b CLI
      assembles it into the (C_env=4, H, W) env tensor.
"""
from __future__ import annotations

import calendar
import gzip
import os
import pathlib
import shutil
from typing import Callable, Iterable

import numpy as np
import rasterio
import rioxarray  # noqa: F401 — registers the .rio accessor
import xarray as xr

from mal_commonlib.aoi import AOI


CHIRPS_NODATA: float = -9999.0
CHIRPS_DAILY_TIF_GZ_TEMPLATE = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/{year}/"
    "chirps-v2.0.{year:04d}.{month:02d}.{day:02d}.tif.gz"
)


# -- helpers ----------------------------------------------------------------


def _default_cache_dir() -> pathlib.Path:
    """XDG cache dir for CHIRPS downloads: ``$XDG_CACHE_HOME/mal_commonlib/chirps``
    or ``~/.cache/mal_commonlib/chirps`` if the env var is unset."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "chirps"


def _days_in_month(year: int, month: int) -> list[int]:
    n = calendar.monthrange(year, month)[1]
    return list(range(1, n + 1))


def _daily_url_for(year: int, month: int, day: int) -> str:
    return CHIRPS_DAILY_TIF_GZ_TEMPLATE.format(year=year, month=month, day=day)


def _download_to(url: str, dest: pathlib.Path, *, timeout: int = 120) -> pathlib.Path:
    """Stream ``url`` to ``dest`` (skip if already cached)."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
        shutil.move(str(tmp), str(dest))
    return dest


def _read_chirps_tif_gz(path: pathlib.Path, aoi: AOI) -> xr.DataArray:
    """Open a CHIRPS daily gzipped GeoTIFF, clip to the AOI bbox, return a
    single-band (y, x) DataArray in EPSG:4326 with CHIRPS nodata -> NaN."""
    import rasterio.windows

    with rasterio.open(str(path)) as src:
        if src.count != 1:
            raise ValueError(
                f"CHIRPS daily GeoTIFF {path} has {src.count} bands; expected 1"
            )
        w, s, e, n = aoi.bbox
        # rasterio windows.from_bounds needs the source bounds in source CRS;
        # CHIRPS is in EPSG:4326 and the AOI is EPSG:4326 in the typical v1 case.
        src_crs = src.crs
        aoi_crs = aoi.crs_obj
        if not aoi_crs.equals(src_crs):
            from pyproj import Transformer

            t = Transformer.from_crs(aoi_crs, src_crs, always_xy=True)
            xs = [w, e, e, w]
            ys = [s, s, n, n]
            xs, ys = t.transform(xs, ys)
            w_, s_ = min(xs), min(ys)
            e_, n_ = max(xs), max(ys)
        else:
            w_, s_, e_, n_ = w, s, e, n
        win = rasterio.windows.from_bounds(w_, s_, e_, n_, src.transform)
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        if win.width <= 0 or win.height <= 0:
            raise ValueError(
                f"AOI bbox {aoi.bbox} does not overlap CHIRPS raster bounds "
                f"({src.bounds})"
            )
        arr = src.read(1, window=win)
        transform = src.window_transform(win)
        nodata = src.nodata
    da = xr.DataArray(
        np.asarray(arr, dtype=np.float32),
        dims=("y", "x"),
        coords={
            "y": np.arange(arr.shape[0]) * transform.e + transform.f,
            "x": np.arange(arr.shape[1]) * transform.a + transform.c,
        },
    )
    da.rio.write_crs(src_crs, inplace=True)
    # CHIRPS uses -9999.0 as nodata; if the file has no nodata tag, mask the
    # same sentinel value to NaN. Land/ocean mask handled by the loader.
    sentinel = nodata if nodata is not None else CHIRPS_NODATA
    da = da.where(da != sentinel)
    return da


def _monthly_total_from_rasters(
    rasters: Iterable[xr.DataArray],
    aoi: AOI,
) -> xr.DataArray:
    """Sum daily CHIRPS (mm/day) into a monthly total (mm), aligned on the
    AOI's grid in EPSG:4326. NaN where any day is NaN.

    The output is on the daily 0.05° grid clipped to the AOI bbox; per-cell
    reprojection to the AOI's ``resolution_m`` grid happens in the next step.
    """
    rasters = list(rasters)
    if not rasters:
        raise ValueError("monthly total needs at least one daily raster")
    summed = rasters[0].copy()
    for da in rasters[1:]:
        # Align on the first raster's grid (CHIRPS daily is co-aligned).
        summed = summed + da
    # CHIRPS daily units are mm/day; sum over the month is monthly total mm.
    return summed.astype(np.float32)


def _ref_grid_for_aoi(aoi: AOI) -> xr.DataArray:
    """Build a 1-pixel reference DataArray in ``aoi.crs`` covering the AOI bbox
    with the shape needed to reproject into. The actual values are unused; only
    the shape/transform/CRS are used by ``rioxarray.reproject_match``."""
    import rasterio.transform

    h, w = aoi.cells_per_side()
    w_, s_, e_, n_ = aoi.bbox
    transform = rasterio.transform.from_bounds(w_, s_, e_, n_, w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    da = xr.DataArray(arr, dims=("y", "x"))
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    return da


def _reproject_to_aoi_grid(
    monthly_total: xr.DataArray,
    aoi: AOI,
) -> np.ndarray:
    """Reproject the monthly total (EPSG:4326) to the AOI's target grid."""
    ref = _ref_grid_for_aoi(aoi)
    rep = monthly_total.rio.reproject_match(ref, resampling=rasterio.enums.Resampling.bilinear)
    return np.asarray(rep.values, dtype=np.float32)


def _normalize_rainfall(rain_mm: np.ndarray) -> tuple[np.ndarray, float]:
    """Min-max normalize a (H, W) array over the AOI's wet-season P95 (v1 proxy).

    Returns ``(normalized, cap_mm)`` where ``normalized`` is in [0, 1] and
    ``cap_mm`` is the P95 value used as the cap. Both NaN and ``-9999.0`` are
    treated as NoData and re-emitted as ``-9999.0`` so the env writer can
    hand the result to rasterio without surprises.

    .. note::
        Retained as a helper for tests and downstream normalization (e.g.
        if a future loader wants a pre-normalized [0, 1] band). The public
        ``load_chirps_rainfall`` does **not** apply this function: it
        returns the raw mm field and exposes the cap via the
        ``rainfall_cap_mm`` attribute on the returned DataArray for
        documentation / sidecar use only.
    """
    nodata_mask = (~np.isfinite(rain_mm)) | (rain_mm == CHIRPS_NODATA)
    finite = rain_mm[~nodata_mask]
    if finite.size == 0:
        out = np.full(rain_mm.shape, CHIRPS_NODATA, dtype=np.float32)
        return out, 0.0
    cap = float(np.nanpercentile(finite, 95))
    out = np.full(rain_mm.shape, CHIRPS_NODATA, dtype=np.float32)
    if not np.isfinite(cap) or cap < 1e-9:
        # No rain anywhere in the AOI: all finite cells normalize to 0.0.
        out[~nodata_mask] = 0.0
        return out, 0.0
    out[~nodata_mask] = np.clip(rain_mm[~nodata_mask] / cap, 0.0, 1.0).astype(np.float32)
    return out, cap


# -- public API -------------------------------------------------------------


def load_chirps_rainfall(
    aoi: AOI,
    year: int,
    month: int,
    *,
    cache_dir: pathlib.Path | None = None,
    _fetch_daily: Callable[[int, int, int], xr.DataArray] | None = None,
) -> xr.DataArray:
    """Load CHIRPS v2.0 daily precipitation for the given AOI and month.

    Aggregates daily 0.05° (~5 km) to monthly total mm for the AOI's bbox,
    reprojected to the AOI's grid. Returns the **raw monthly total in mm**
    (no P95 normalization). The suitability overlay
    (``mal_ghana_sim.suitability.suitability_from_stack``) re-normalizes
    its inputs via its own min-max, so the loader's normalization is
    redundant — and harmful to the ABM, which compares the env band
    against ``RAIN_THRESHOLD_MM = 15`` to activate habitat patches.

    The AOI-internal P95 of the monthly-total field is still computed and
    exposed via the ``rainfall_cap_mm`` attribute for documentation /
    sidecar use.

    Args:
        aoi: the AOI (bbox, CRS, resolution_m, slug).
        year, month: 1-indexed month.
        cache_dir: optional local cache for downloaded GeoTIFFs. If None,
                   uses ``$XDG_CACHE_HOME/mal_commonlib/chirps`` (or
                   ``~/.cache/mal_commonlib/chirps``).
        _fetch_daily: testing hook — a callable ``(year, month, day) ->
            xr.DataArray`` that bypasses the network download. Production
            code should leave this as ``None``.

    Returns:
        xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
        Values in mm/month (raw monthly total, typically 0–500 for Ghana's
        wet season). ``-9999.0`` for cells outside the AOI bbox or where
        the source has no data.

    Raises:
        FileNotFoundError: if a daily file is missing (HTTP 404) and no
            ``_fetch_daily`` override is supplied.
        requests.HTTPError: for any other HTTP error.
    """
    if not (1 <= month <= 12):
        raise ValueError(f"month must be in 1..12; got {month}")
    if year < 1981:
        raise ValueError(f"CHIRPS starts in 1981; got year={year}")

    if _fetch_daily is None:
        cdir = cache_dir if cache_dir is not None else _default_cache_dir()

        def _default_fetch(y: int, m: int, d: int) -> xr.DataArray:
            url = _daily_url_for(y, m, d)
            gz = cdir / f"chirps-v2.0.{y:04d}.{m:02d}.{d:02d}.tif.gz"
            tif = gz.with_suffix("")  # drop .gz
            if not tif.exists():
                _download_to(url, gz)
                with gzip.open(gz, "rb") as f_in, open(tif, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return _read_chirps_tif_gz(tif, aoi)

        fetch = _default_fetch
    else:
        fetch = _fetch_daily

    daily_rasters = [fetch(year, month, d) for d in _days_in_month(year, month)]
    monthly = _monthly_total_from_rasters(daily_rasters, aoi)
    rain_mm = _reproject_to_aoi_grid(monthly, aoi)
    # Compute the P95 cap for documentation / sidecar, but do NOT apply
    # the normalization: the env band is raw mm so the ABM's RAIN_THRESHOLD_MM
    # check (15 mm) is meaningful, and suitability re-normalizes anyway.
    _normalized, cap_mm = _normalize_rainfall(rain_mm)
    # Preserve the original NoData semantics: every cell is either a raw
    # mm value or CHIRPS_NODATA (-9999.0). NaN would break a downstream
    # comparison like ``rain_24h > 15`` in the ABM and is not a valid
    # GeoTIFF float32 value.
    nodata_mask = (~np.isfinite(rain_mm)) | (rain_mm == CHIRPS_NODATA)
    rain_mm = np.where(nodata_mask, np.float32(CHIRPS_NODATA), rain_mm.astype(np.float32))

    h, w = aoi.cells_per_side()
    assert rain_mm.shape == (h, w), (
        f"rain_mm shape {rain_mm.shape} != AOI grid {(h, w)}"
    )
    da = xr.DataArray(
        rain_mm.astype(np.float32),
        dims=("y", "x"),
        attrs={
            "long_name": "CHIRPS v2.0 monthly total precipitation",
            "units": "mm/month",
            "source": "CHIRPS v2.0 daily 0.05°",
            "aoi_slug": aoi.slug,
            "year": year,
            "month": month,
            "nodata": CHIRPS_NODATA,
            "rainfall_cap_mm": float(cap_mm),
        },
    )
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    return da


__all__ = ["load_chirps_rainfall", "CHIRPS_NODATA"]
