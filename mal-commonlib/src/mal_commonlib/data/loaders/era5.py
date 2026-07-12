"""ERA5-Land daily statistics loader (M1.3a, channel: temp_suitability).

Public surface:
    load_era5_temp_suitability(aoi, year, month, *, cache_dir=None) -> xr.DataArray
    sharpe_demichele_growth(T_celsius: xr.DataArray) -> xr.DataArray

Source: Copernicus CDS — ``derived-era5-land-daily-statistics`` dataset.
Variable: ``2m_temperature`` (daily mean, K).

Auth:
    ERA5-Land requires CDS API credentials (``~/.cdsapirc`` or
    ``CDSAPI_URL``/``CDSAPI_KEY`` env vars). In an env without those, the
    loader raises ``RuntimeError`` with a clear message. See
    ``op-m1-3a-data-layer-auth`` in the project knowledge graph for the
    data-layer auth runbook.

Notes:
    * v1 calibration parameters (T_OPT=25 °C, T_HALF_WIDTH=8 °C) are kept here
      as the v1 reference. The casablanca version in
      ``mal-ghana-sim/src/mal_ghana_sim/config.py`` (``temp_suitability``)
      duplicates the same formula; a follow-up commit imports this one and
      removes the casablanca copy. (Not done in M1.3a to keep the diff
      scoped to the data layer.)
    * Output: ``temp_suitability`` ∈ [0, 1] by construction (per
      docs/abm-output-contract.md §2 channel 2). NoData: -9999.0.
    * This loader only emits a single channel (``temp_suitability``); the
      M1.3b CLI assembles it into the (C_env=4, H, W) env tensor.
"""
from __future__ import annotations

import calendar
import os
import pathlib

import numpy as np
import rasterio
import rioxarray  # noqa: F401 — registers the .rio accessor
import xarray as xr

from mal_commonlib.aoi import AOI


ERA5_NODATA: float = -9999.0
ERA5_DATASET: str = "derived-era5-land-daily-statistics"
ERA5_VARIABLE: str = "2m_temperature"
ERA5_DAILY_STATISTIC: str = "daily_mean"  # daily mean; we aggregate to monthly mean
ERA5_FREQ: str = "1_hourly"               # CDS frequency for daily-statistics dataset

# CDS API requests use the long variable name "2m_temperature", but the
# NetCDF files it ships use the short name "t2m". Map long → short so the
# reader can find the variable in the downloaded file.
ERA5_VARIABLE_NETCDF_ALIAS: dict[str, str] = {
    "2m_temperature": "t2m",
}

# v1 thermal response (Mordecai 2013 parabolic approximation).
T_OPT: float = 25.0
T_HALF_WIDTH: float = 8.0


# -- thermal response -------------------------------------------------------


def sharpe_demichele_growth(T_celsius: xr.DataArray) -> xr.DataArray:
    """Sharpe-DeMichele-style growth response in [0, 1] from 2 m temperature.

    Vectorized xarray implementation. v1 uses a parabolic approximation of
    the original Sharpe-Schoolfield-DeMichele thermal performance curve,
    calibrated with ``T_OPT=25`` and ``T_HALF_WIDTH=8`` (Mordecai 2013).

        s(T) = clip(1 - ((T - T_OPT) / T_HALF_WIDTH)^2, 0, 1)

    Properties:
        * s(T_OPT) == 1.0
        * s(T_OPT ± T_HALF_WIDTH / sqrt(2)) == 0.5
        * s(T_OPT ± T_HALF_WIDTH) == 0.0  (boundary of viable range)
        * s(T) == 0.0 outside the viable range

    Args:
        T_celsius: xarray DataArray of 2 m temperature in degrees Celsius.

    Returns:
        xarray DataArray of the same shape with values in [0, 1].
        Where ``T_celsius`` is NaN, the output is NaN; this is the only
        place NaN propagates — the loader turns NaN into ``ERA5_NODATA``
        after reprojection to the AOI grid.
    """
    z = (T_celsius - T_OPT) / T_HALF_WIDTH
    s = 1.0 - z * z
    return s.clip(0.0, 1.0).astype(np.float32)


# -- helpers ----------------------------------------------------------------


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "era5"


def _days_in_month(year: int, month: int) -> list[str]:
    n = calendar.monthrange(year, month)[1]
    return [f"{d:02d}" for d in range(1, n + 1)]


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
    da: xr.DataArray,
    aoi: AOI,
) -> np.ndarray:
    """Reproject a 2-D DataArray to the AOI's grid; returns float32 (H, W)."""
    ref = _ref_grid_for_aoi(aoi)
    rep = da.rio.reproject_match(ref, resampling=rasterio.enums.Resampling.bilinear)
    return np.asarray(rep.values, dtype=np.float32)


def _monthly_mean_K_to_C(da_K: xr.DataArray, year: int, month: int) -> xr.DataArray:
    """Aggregate a daily (or any) ``2m_temperature`` DataArray to a monthly
    mean in degrees Celsius. The input is expected in Kelvin; this function
    converts to °C and reduces over the leading time axis.

    CDS products use a few different time-axis names — ``time`` for the
    classic ERA5/ERA5-Land monthly products, ``valid_time`` for the
    ``derived-era5-land-daily-statistics`` dataset, and (in forecast
    products) ``date``/``datetime``/``forecast_hour``/``lead_time``. We
    accept any of those; if none is present we fall back to reducing over
    any single non-spatial dim, which covers per-month files that ship
    with a singleton leading axis.
    """
    SPATIAL_DIMS = {"y", "x", "latitude", "longitude", "lat", "lon", "rlat", "rlon"}
    TIME_LIKE = {"time", "valid_time", "date", "datetime", "lead_time", "forecast_hour"}
    time_dim = next((d for d in da_K.dims if d in TIME_LIKE), None)
    if time_dim is not None:
        monthly = da_K.mean(dim=time_dim, skipna=True)
    else:
        non_spatial = [d for d in da_K.dims if d not in SPATIAL_DIMS]
        if len(non_spatial) == 1:
            monthly = da_K.mean(dim=non_spatial[0], skipna=True)
        else:
            monthly = da_K
    return (monthly - 273.15).astype(np.float32)


def _cds_request(year: int, month: int, bbox_wsen: tuple[float, float, float, float]) -> dict:
    """Build a CDS API request for the AOI bbox and (year, month)."""
    w, s, e, n = bbox_wsen
    return {
        "variable": [ERA5_VARIABLE],
        "daily_statistic": [ERA5_DAILY_STATISTIC],
        "year": [f"{year:04d}"],
        "month": [f"{month:02d}"],
        "day": _days_in_month(year, month),
        "time_zone": "utc+00:00",
        "frequency": [ERA5_FREQ],
        "area": [n, w, s, e],  # CDS API: [N, W, S, E]
    }


# -- public API -------------------------------------------------------------


def load_era5_temp_suitability(
    aoi: AOI,
    year: int,
    month: int,
    *,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load ERA5-Land daily stats ``2m_temperature``, aggregate to monthly
    mean, apply the Sharpe-DeMichele growth response, return temp_suitability.

    Args:
        aoi: the AOI.
        year, month: 1-indexed month.
        cache_dir: optional local cache for downloaded NetCDFs.

    Returns:
        xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
        Values in [0, 1] (``temp_suitability``). ``-9999.0`` for NoData.

    Raises:
        RuntimeError: if CDS auth is missing (no ``~/.cdsapirc`` or
            ``CDSAPI_URL``/``CDSAPI_KEY`` env vars). The message points at
            ``op-m1-3a-data-layer-auth`` in the knowledge graph.
    """
    if not (1 <= month <= 12):
        raise ValueError(f"month must be in 1..12; got {month}")
    if year < 1950:
        raise ValueError(f"ERA5 starts in 1950; got year={year}")

    import cdsapi

    # Auth check. cdsapi.Client() raises a plain Exception when the config
    # file is missing/incomplete; convert to RuntimeError with a clear
    # pointer to the runbook.
    try:
        client = cdsapi.Client()
    except Exception as e:
        raise RuntimeError(
            "ERA5-Land requires CDS auth. Configure ~/.cdsapirc or "
            "CDSAPI_URL/KEY env vars. See op-m1-3a-data-layer-auth for "
            f"details. (cdsapi raised: {e})"
        ) from e

    cdir = cache_dir if cache_dir is not None else _default_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    target = cdir / f"era5_{ERA5_VARIABLE}_{year:04d}_{month:02d}.nc"

    if not target.exists():
        request = _cds_request(year, month, aoi.bbox)
        result = client.retrieve(ERA5_DATASET, request, target=str(target))
        # cdsapi's Result.download() will only re-download if ``target`` is
        # not already on disk. Force a download path for clarity.
        if not target.exists():
            result.download(str(target))

    ds = xr.open_dataset(str(target))
    if ERA5_VARIABLE in ds.data_vars or ERA5_VARIABLE in ds:
        var_name = ERA5_VARIABLE
    elif ERA5_VARIABLE in ERA5_VARIABLE_NETCDF_ALIAS and (
        ERA5_VARIABLE_NETCDF_ALIAS[ERA5_VARIABLE] in ds.data_vars
        or ERA5_VARIABLE_NETCDF_ALIAS[ERA5_VARIABLE] in ds
    ):
        var_name = ERA5_VARIABLE_NETCDF_ALIAS[ERA5_VARIABLE]
    else:
        # Some products use capitalisation; fall back to first 2m_temperature-like var.
        candidates = [v for v in ds.data_vars if "temper" in v.lower() and "2m" in v.lower()]
        if not candidates:
            raise KeyError(
                f"ERA5 dataset {target} has no '{ERA5_VARIABLE}' or alias found; "
                f"available: {list(ds.data_vars)}"
            )
        var_name = candidates[0]
    da_K = ds[var_name]
    if "expver" in da_K.dims:
        # CDS sometimes ships both ecmwf versions on the same axis; pick the
        # latest (the most recent dataset version) and average.
        da_K = da_K.sel(expver=da_K.coords["expver"].max())

    monthly_C = _monthly_mean_K_to_C(da_K, year, month)
    suit = sharpe_demichele_growth(monthly_C)

    # Drop dims that aren't (y, x) so reproject_match has a clean 2-D array.
    suit_2d = suit.squeeze(drop=True)
    # Make sure it has a CRS; ERA5 is in EPSG:4326 by default.
    if suit_2d.rio.crs is None:
        suit_2d.rio.write_crs("EPSG:4326", inplace=True)

    arr = _reproject_to_aoi_grid(suit_2d, aoi)
    nan_mask = ~np.isfinite(arr)
    out = arr.copy()
    out[nan_mask] = ERA5_NODATA
    out[~nan_mask] = np.clip(out[~nan_mask], 0.0, 1.0)

    h, w = aoi.cells_per_side()
    assert out.shape == (h, w), f"out shape {out.shape} != AOI grid {(h, w)}"

    da = xr.DataArray(
        out.astype(np.float32),
        dims=("y", "x"),
        attrs={
            "long_name": "temp_suitability (Sharpe-DeMichele growth response)",
            "units": "normalized (parabolic, T_OPT=25, T_HALF_WIDTH=8)",
            "source": f"ERA5-Land daily stats {ERA5_VARIABLE} {ERA5_DAILY_STATISTIC}",
            "aoi_slug": aoi.slug,
            "year": year,
            "month": month,
            "nodata": ERA5_NODATA,
        },
    )
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    return da


__all__ = [
    "load_era5_temp_suitability",
    "sharpe_demichele_growth",
    "T_OPT",
    "T_HALF_WIDTH",
    "ERA5_NODATA",
    "ERA5_DATASET",
    "ERA5_VARIABLE",
]
