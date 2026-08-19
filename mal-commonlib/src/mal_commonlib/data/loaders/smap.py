"""SMAP RSS L3 SSS monthly sea surface salinity loader (M7.8 — ``salinity`` channel).

Public surface
--------------
``load_smap_salinity(aoi, *, years, months=None, cache_dir=None) -> xr.DataArray``
``load_smap_salinity_synthetic(aoi, *, years, months=None, source=None) -> xr.DataArray``

Source
------
Remote Sensing Systems (RSS) SMAP Sea Surface Salinity (SSS) Level 3
Standard Mapped Image (SMI) **Monthly V6.0** (validated), distributed by
PO.DAAC / NASA Earthdata.

    Dataset id : SMAP_RSS_L3_SSS_SMI_MONTHLY_V6
    DOI        : 10.5067/SMP60-3SMCS
    Grid       : 0.25° × 0.25° (WGS-84), longitude 0..360
    Variables  : sss_smap (70 km standard), sss_smap_40km (40 km),
                 fland / gland (land fraction), uncertainties
    Units      : practical salinity units (PSU/PSS); raw stored ×1000, fill -9999

Output contract
---------------
    * dims ``(time, y, x)`` — ``(y, x)`` when a single month is requested
    * coordinates ``y`` / ``x`` = SMAP 0.25° lat/lon grid clipped to the AOI
      bbox, longitude converted to [-180, 180]
    * dtype float32, CRS = EPSG:4326
    * values in PSU (raw × 1e-3); NaN for land / fill / no-data cells
    * ``units`` attr = ``'psu'``

Known mission gaps: SMAP was out of science mode 2019-06-19..07-23 and
2022-08-09..10-06. Those months have no granules → the loader returns an
all-NaN slice (the ingest layer converts no-data to 0.0 freshwater). It
does not crash on a missing month.

The heavy parts (earthaccess auth / search / download, opening the real
netCDF) are injected via the ``_fetch_monthly`` keyword hook, mirroring
``_fetch_daily`` in chirps.py, so tests run offline against synthetic
sources.
"""
from __future__ import annotations

import logging
import os
import pathlib
import tempfile
from collections.abc import Iterable, Sequence

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr

from mal_commonlib.aoi import AOI

log = logging.getLogger(__name__)

_DATASET_ID = "SMAP_RSS_L3_SSS_SMI_MONTHLY_V6"
_FILL = -9999.0
_SCALE = 1e-3
_NODATA_OUT = -9999.0
_LAND_FRACTION_THRESHOLD = 0.5
_GRID_STEP = 0.25

_BASE_ATTRS = {
    "long_name": "SMAP RSS L3 sea surface salinity (monthly)",
    "units": "psu",
    "source": "SMAP RSS SSS V6.0",
    "nodata": _NODATA_OUT,
}


# -- helpers ----------------------------------------------------------------

def _ensure_cache_dir(cache_dir: pathlib.Path | None) -> pathlib.Path:
    """Default cache: ``$XDG_CACHE_HOME/mal_commonlib/smap`` or tmpdir fallback."""
    if cache_dir is None:
        base = os.environ.get("XDG_CACHE_HOME")
        if base:
            cache_dir = pathlib.Path(base) / "mal_commonlib" / "smap"
        else:
            cache_dir = pathlib.Path(tempfile.gettempdir()) / "mal_commonlib" / "smap"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _earthaccess_login() -> None:
    """Authenticate earthaccess via the EARTHDATA_TOKEN env var (mirrors modis)."""
    if not os.environ.get("EARTHDATA_TOKEN"):
        raise RuntimeError(
            "EARTHDATA_TOKEN env var is not set; the SMAP loader needs it to "
            "authenticate against NASA Earthdata. Generate a token at "
            "https://urs.earthdata.nasa.gov/user_tokens and export it."
        )
    import earthaccess  # lazy so the module imports even if earthaccess is broken

    earthaccess.login()


def _search_window(year: int, month: int) -> tuple[str, str]:
    start = f"{year:04d}-{month:02d}-01"
    start_dt = np.datetime64(start, "D")
    end_dt = (start_dt + np.timedelta64(1, "M")) - np.timedelta64(1, "D")
    return start, str(end_dt)


def _bbox_4326(aoi: AOI) -> tuple[float, float, float, float]:
    """(W, S, E, N) in WGS-84 for earthaccess.search_data bounding_box.

    earthaccess wants lon/lat regardless of the AOI's CRS. SMAP ships on a
    0..360 longitude grid; easthack: geographic CRS values are returned as-is
    (-180..180 form) — the mid-Pacific 0..360 conversion is handled when
    reading each granule in ``_postprocess_smap_ds``.
    """
    import pyproj

    if aoi.crs_obj.is_geographic:
        return tuple(float(v) for v in aoi.bbox)
    t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
    w, s, e, n = aoi.bbox
    w, s = t.transform(w, s)
    e, n = t.transform(e, n)
    return float(w), float(s), float(e), float(n)


def _aoi_native_grid(aoi: AOI) -> tuple[np.ndarray, np.ndarray]:
    """SMAP 0.25° grid points (lat, lon) covering the AOI bbox in EPSG:4326.

    Grid points are the SMAP half-pixel coordinates ``0.125 + 0.25*k``.
    Used both to reindex real granules onto a canonical grid and to build
    the all-NaN slices that fill mission gaps, so all months align.
    """
    w, s, e, n = _bbox_4326(aoi)
    y = np.arange(np.floor(s / _GRID_STEP) * _GRID_STEP + 0.125, n, _GRID_STEP)
    x = np.arange(np.floor(w / _GRID_STEP) * _GRID_STEP + 0.125, e, _GRID_STEP)
    return y.astype(np.float64), x.astype(np.float64)


def _write_crs_transform(da: xr.DataArray, w: float, s: float, e: float, n: float) -> None:
    h, width = da.shape
    da.rio.write_crs("EPSG:4326", inplace=True)
    da.rio.write_transform(from_bounds(w, s, e, n, width, h), inplace=True)


def _empty_month(aoi: AOI) -> xr.DataArray:
    """All-NaN monthly slice on the AOI-clipped SMAP grid (mission gap)."""
    y, x = _aoi_native_grid(aoi)
    arr = np.full((len(y), len(x)), np.nan, dtype=np.float32)
    da = xr.DataArray(
        arr, dims=("y", "x"), name="salinity",
        coords={"y": y, "x": x}, attrs=dict(_BASE_ATTRS),
    )
    _write_crs_transform(da, *_bbox_4326(aoi))
    return da


def _postprocess_smap_ds(raw: xr.Dataset, aoi: AOI) -> xr.DataArray:
    """Convert one raw SMAP monthly granule to an AOI-clipped PSU DataArray.

    Steps:
        1. variable selection — ``sss_smap_40km`` (coastal MVP) with fallback
           to ``sss_smap`` (70 km standard); land fraction ``fland``/``gland``.
        2. longitude 0..360 → -180..180, sort both dims.
        3. clip to the AOI bbox.
        4. apply scale 1e-3 and mask fill -9999 → NaN.
        5. mask continental cells from ``fland``/``gland`` (>0.5 land) → NaN.
    """
    if "sss_smap_40km" in raw:
        da = raw["sss_smap_40km"]
        land = raw["fland"] if "fland" in raw else raw.get("gland")
    elif "sss_smap" in raw:
        da = raw["sss_smap"]
        land = raw.get("gland", raw.get("fland"))
    else:
        raise ValueError(
            f"SMAP dataset has no sss_smap_40km/sss_smap variable; "
            f"vars={sorted(raw.data_vars)}"
        )

    da = _to_neg180(da)
    if land is not None:
        land = _to_neg180(land).reindex(lat=da.lat.values, lon=da.lon.values)

    w, s, e, n = _bbox_4326(aoi)
    da = da.sel(lat=slice(s, n), lon=slice(w, e))
    if land is not None:
        land = land.sel(lat=slice(s, n), lon=slice(w, e))

    vals = da.values.astype(np.float32)
    fill = (vals == np.float32(_FILL)) | ~np.isfinite(vals)
    arr = np.where(fill, np.nan, vals * np.float32(_SCALE)).astype(np.float32)
    arr = np.where((arr < 0.0) | (arr > 45.0), np.nan, arr)

    if land is not None:
        lf = land.values.astype(np.float32)
        if np.nanmax(lf) > 1.5:
            lf = lf / 100.0
        land_mask = (lf > _LAND_FRACTION_THRESHOLD) & np.isfinite(lf)
        arr = np.where(land_mask, np.nan, arr)

    out = xr.DataArray(
        arr, dims=("y", "x"), name="salinity",
        coords={"y": da.lat.values.astype(np.float64), "x": da.lon.values.astype(np.float64)},
        attrs=dict(_BASE_ATTRS),
    )
    _write_crs_transform(out, w, s, e, n)
    return out


def _to_neg180(da: xr.DataArray) -> xr.DataArray:
    """Convert a 0..360 longitude grid to -180..180 and sort both dims."""
    lon = ((da.lon.values.astype(np.float64) + 180.0) % 360.0) - 180.0
    da = da.assign_coords(lon=lon)
    da = da.sortby(["lat", "lon"])
    return da


def _fetch_monthly_via_earthaccess(
    aoi: AOI, year: int, month: int, cache: pathlib.Path
) -> xr.Dataset | None:
    """Zero the real (network) path: search PO.DAAC, download, open the granule.

    Returns None for a missing month (mission gap) or a failed search, so
    the caller emits an all-NaN slice instead of crashing.
    """
    _earthaccess_login()
    import earthaccess

    start, end = _search_window(year, month)
    bbox = _bbox_4326(aoi)
    try:
        results = earthaccess.search_data(
            short_name=_DATASET_ID,
            temporal=(start, end),
            bounding_box=bbox,
        )
    except Exception as exc:  # noqa: BLE001 — treat any net/auth failure as a gap
        log.warning("SMAP search failed %s-%s: %s", year, month, exc)
        return None
    if not results:
        return None  # 2019-06..07 / 2022-08..10 mission gaps have no granules

    paths = earthaccess.download(results, local_path=str(cache))
    flat: list[pathlib.Path] = []
    for p in paths:
        if isinstance(p, (list, tuple)):
            flat.extend(pathlib.Path(str(x)) for x in p)
        else:
            flat.append(pathlib.Path(str(p)))
    for p in flat:
        if p.exists():
            try:
                return xr.open_dataset(p)
            except Exception as exc:  # noqa: BLE001
                log.warning("SMAP open failed %s: %s", p, exc)

    # Fallback: OPENDAP data links when no local download occurred.
    try:
        for link in results[0].data_links():
            if ".nc" in link:
                return xr.open_dataset(link, engine="netcdf4")
    except Exception as exc:  # noqa: BLE001
        log.warning("SMAP OPENDAP open failed %s-%s: %s", year, month, exc)
    return None


# -- public API -------------------------------------------------------------

def load_smap_salinity(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,
    cache_dir: pathlib.Path | None = None,
    _fetch_monthly: "callable | None" = None,
) -> xr.DataArray:
    """Load SMAP RSS L3 SSS monthly sea surface salinity for the AOI.

    Args:
        aoi: the AOI.
        years: sequence of years to load.
        months: 1-indexed months. None = all 12.
        cache_dir: optional local cache for downloaded granules.
        _fetch_monthly: testing hook (kw-only). ``(year, month) ->
            xr.Dataset | None`` returning a raw SMAP granule, or None for a
            month with no data.

    Returns:
        xr.DataArray dims ``(time, y, x)``; ``(y, x)`` if a single month.
        Values in PSU on the AOI-clipped SMAP 0.25° grid, CRS EPSG:4326.
        NaN for land / fill / missing months.
    """
    if months is None:
        months = list(range(1, 13))

    cache = _ensure_cache_dir(cache_dir)

    if _fetch_monthly is None:

        def _default_fetch(y: int, m: int) -> xr.Dataset | None:
            return _fetch_monthly_via_earthaccess(aoi, y, m, cache)

        fetch = _default_fetch
    else:
        fetch = _fetch_monthly

    y_canon, x_canon = _aoi_native_grid(aoi)
    results: list[xr.DataArray] = []
    time_coords: list[np.datetime64] = []

    for year in sorted(years):
        for month in sorted(months):
            if not (1 <= month <= 12):
                raise ValueError(f"month must be in 1..12; got {month}")

            raw = fetch(year, month)
            da = _postprocess_smap_ds(raw, aoi) if raw is not None else _empty_month(aoi)
            da = da.reindex(y=y_canon, x=x_canon)
            results.append(da)
            time_coords.append(np.datetime64(f"{year:04d}-{month:02d}-01"))

    if len(results) == 1:
        out = results[0]
        out.attrs.update(_BASE_ATTRS)
        return out

    stacked = xr.concat(results, dim="time")
    stacked = stacked.assign_coords(time=time_coords)
    stacked.attrs.update(_BASE_ATTRS)
    stacked.rio.write_crs("EPSG:4326", inplace=True)
    return stacked


def load_smap_salinity_synthetic(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,
    source: xr.Dataset | None = None,
) -> xr.DataArray:
    """Fixture-friendly path: build a salinity DataArray with no network.

    Feeds a synthetic raw SMAP granule through the same post-processing
    (scale, lon conversion, land/fill masking) as the real loader, so tests
    exercise exactly the logic the live path uses.

    Args:
        aoi: the AOI.
        years: years to include.
        months: months to include (None = all 12).
        source: optional raw synthetic xr.Dataset. Defaults to a global
            0.25° grid with ``sss_smap_40km`` (ocean = ``33000`` raw → 33 PSU)
            and ``fland`` (1.0 for lat > 10) so both ocean value and land
            mask are present.

    Returns:
        xr.DataArray in PSU, dims ``(time, y, x)``, CRS EPSG:4326.
    """
    if months is None:
        months = list(range(1, 13))
    if source is None:
        source = _synthetic_raw_ds(aoi)

    def _fetch(year: int, month: int) -> xr.Dataset:
        return source

    return load_smap_salinity(
        aoi, years=years, months=months, _fetch_monthly=_fetch
    )


def _synthetic_raw_ds(aoi: AOI, *, ocean_raw: float = 33000.0) -> xr.Dataset:
    """Global 0.25° synthetic SMAP granule: 33 PSU ocean, land band, one fill cell.

    Land fraction ``fland`` = 1.0 for lat > 10 (covers the interior of the
    Ghana AOI whose bbox spans 4.5..11.5° N). A fill cell is placed at
    (5.0° N, 359.875° E) — after lon conversion that longitude is -0.125°,
    inside the Ghana bbox — to exercise fill masking.
    """
    lon = np.arange(0.125, 360.0, _GRID_STEP)
    lat = np.arange(-89.875, 90.0, _GRID_STEP)
    nlat, nlon = len(lat), len(lon)

    sss = np.full((nlat, nlon), np.float32(ocean_raw), dtype=np.float32)
    fland = np.zeros((nlat, nlon), dtype=np.float32)

    land_rows = lat > 10.0
    sss[land_rows, :] = np.float32(_FILL)
    fland[land_rows, :] = 1.0

    lat_idx = int(np.argmin(np.abs(lat - 5.0)))
    lon_idx = int(np.argmin(np.abs(lon - 359.875)))
    sss[lat_idx, lon_idx] = np.float32(_FILL)

    return xr.Dataset(
        {
            "sss_smap_40km": (("lat", "lon"), sss),
            "fland": (("lat", "lon"), fland),
        },
        coords={"lat": lat, "lon": lon},
        attrs={"synthetic": True, "source": "synthetic test fixture"},
    )


DOWNLOADER = {
    "name": "smap",
    "description": "SMAP RSS L3 sea surface salinity: monthly ocean PSU",
    "requires_auth": ["earthdata"],
    "is_time_series": True,
    "outputs": {
        "salinity": load_smap_salinity,
    },
    "formats": {
        "salinity": "monthly_nc",
    },
    "manifest_keys": {
        "salinity": "smap_salinity",
    },
}


__all__ = [
    "load_smap_salinity",
    "load_smap_salinity_synthetic",
    "FILL",
    "DOWNLOADER",
]
FILL = _FILL