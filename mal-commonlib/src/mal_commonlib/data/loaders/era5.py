"""ERA5-Land daily statistics loader (M1.3a, channel: temp_suitability).

Public surface:
    load_era5_temp_suitability(aoi, *, years, months=None, cache_dir=None) -> xr.DataArray
    load_era5_water_temp(aoi, *, years, months=None, cache_dir=None) -> xr.DataArray
    load_era5_wind_6hourly(aoi, *, years, months=None, cache_dir=None) -> xr.Dataset
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
      as the v1 reference. The same formula is implemented in the C++ ABM
      engine (``mal-core/src/mal_core/abm/include/mal_abm_fast/climate.hpp``,
      ``temp_suitability``); the former Python copy lived in the removed
      ``mal-ghana-sim`` experiment package (config.py).
    * Output: ``temp_suitability`` ∈ [0, 1] by construction (per
      docs/abm-output-contract.md §2 channel 2). NoData: -9999.0.
    * This loader only emits a single channel (``temp_suitability``); the
      M1.3b CLI assembles it into the (C_env=4, H, W) env tensor.
"""
from __future__ import annotations

import calendar
import os
import pathlib
from collections.abc import Sequence

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


def _load_era5_temp_suitability_single(
    aoi: AOI,
    year: int,
    month: int,
    cache_dir: pathlib.Path,
) -> xr.DataArray:
    """Load a single (year, month) of ERA5 temp suitability for the AOI."""
    import cdsapi

    try:
        client = cdsapi.Client()
    except Exception as e:
        raise RuntimeError(
            "ERA5-Land requires CDS auth. Configure ~/.cdsapirc or "
            "CDSAPI_URL/KEY env vars. See op-m1-3a-data-layer-auth for "
            f"details. (cdsapi raised: {e})"
        ) from e

    target = cache_dir / f"era5_{ERA5_VARIABLE}_{year:04d}_{month:02d}.nc"

    if not target.exists():
        request = _cds_request(year, month, aoi.bbox)
        result = client.retrieve(ERA5_DATASET, request, target=str(target))
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
        candidates = [v for v in ds.data_vars if "temper" in v.lower() and "2m" in v.lower()]
        if not candidates:
            raise KeyError(
                f"ERA5 dataset {target} has no '{ERA5_VARIABLE}' or alias found; "
                f"available: {list(ds.data_vars)}"
            )
        var_name = candidates[0]
    da_K = ds[var_name]
    if "expver" in da_K.dims:
        da_K = da_K.sel(expver=da_K.coords["expver"].max())

    monthly_C = _monthly_mean_K_to_C(da_K, year, month)
    suit = sharpe_demichele_growth(monthly_C)

    suit_2d = suit.squeeze(drop=True)
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


def load_era5_temp_suitability(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load ERA5-Land daily stats temp suitability for year(s) × month(s).

    Args:
        aoi: the AOI.
        years: sequence of years to load.
        months: sequence of 1-indexed months. None = all 12.
        cache_dir: optional local cache for downloaded NetCDFs.

    Returns:
        xr.DataArray with dtype float32, CRS = aoi.crs.
        2-D (y, x) if single month, 3-D (time, y, x) if multiple.
        Values in [0, 1]. ``-9999.0`` for NoData.
    """
    if months is None:
        months = list(range(1, 13))

    cdir = cache_dir if cache_dir is not None else _default_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)

    results: list[xr.DataArray] = []
    time_coords: list[np.datetime64] = []

    for year in sorted(years):
        for month in sorted(months):
            if not (1 <= month <= 12):
                raise ValueError(f"month must be in 1..12; got {month}")
            if year < 1950:
                raise ValueError(f"ERA5 starts in 1950; got year={year}")
            da = _load_era5_temp_suitability_single(aoi, year, month, cdir)
            results.append(da)
            time_coords.append(np.datetime64(f"{year:04d}-{month:02d}-01"))

    if len(results) == 1:
        return results[0]

    stacked = xr.concat(results, dim="time")
    stacked = stacked.assign_coords(time=time_coords)
    stacked.attrs.update({
        "long_name": "temp_suitability (Sharpe-DeMichele growth response)",
        "units": "normalized (parabolic, T_OPT=25, T_HALF_WIDTH=8)",
        "source": f"ERA5-Land daily stats {ERA5_VARIABLE} {ERA5_DAILY_STATISTIC}",
        "aoi_slug": aoi.slug,
        "nodata": ERA5_NODATA,
    })
    stacked.rio.write_crs(aoi.crs_obj, inplace=True)
    return stacked


def _load_era5_water_temp_single(
    aoi: AOI,
    year: int,
    month: int,
    cache_dir: pathlib.Path,
) -> xr.DataArray:
    """Load a single (year, month) of ERA5 daily water temp for the AOI."""
    import cdsapi

    try:
        client = cdsapi.Client()
    except Exception as e:
        raise RuntimeError(
            "ERA5-Land requires CDS auth. Configure ~/.cdsapirc or "
            "CDSAPI_URL/KEY env vars. See op-m1-3a-data-layer-auth for "
            f"details. (cdsapi raised: {e})"
        ) from e

    target = cache_dir / f"era5_{ERA5_VARIABLE}_{year:04d}_{month:02d}.nc"

    if not target.exists():
        request = _cds_request(year, month, aoi.bbox)
        result = client.retrieve(ERA5_DATASET, request, target=str(target))
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
        candidates = [v for v in ds.data_vars if "temper" in v.lower() and "2m" in v.lower()]
        if not candidates:
            raise KeyError(
                f"ERA5 dataset {target} has no '{ERA5_VARIABLE}' or alias found; "
                f"available: {list(ds.data_vars)}"
            )
        var_name = candidates[0]
    da_K = ds[var_name]
    if "expver" in da_K.dims:
        da_K = da_K.sel(expver=da_K.coords["expver"].max())

    SPATIAL_DIMS = {"y", "x", "latitude", "longitude", "lat", "lon", "rlat", "rlon"}
    TIME_LIKE = {"time", "valid_time", "date", "datetime", "lead_time", "forecast_hour"}
    time_dim = next((d for d in da_K.dims if d in TIME_LIKE), None)
    if time_dim is None:
        non_spatial = [d for d in da_K.dims if d not in SPATIAL_DIMS]
        time_dim = non_spatial[0] if non_spatial else None

    da_C = (da_K - 273.15).astype(np.float32)
    if time_dim is not None:
        da_C = da_C.rename({time_dim: "time"})

    drop_dims = [d for d in da_C.dims if d not in ("time", "y", "x", "latitude", "longitude")]
    if drop_dims:
        da_C = da_C.squeeze(drop_dims, drop=True)

    ref = _ref_grid_for_aoi(aoi)
    daily_arrays: list[np.ndarray] = []
    if "time" in da_C.dims:
        for t in range(da_C.sizes["time"]):
            slice_2d = da_C.isel(time=t).squeeze(drop=True)
            if slice_2d.rio.crs is None:
                slice_2d.rio.write_crs("EPSG:4326", inplace=True)
            arr = _reproject_to_aoi_grid(slice_2d, aoi)
            daily_arrays.append(arr)
        time_coords = da_C.coords["time"].values
    else:
        if da_C.rio.crs is None:
            da_C.rio.write_crs("EPSG:4326", inplace=True)
        arr = _reproject_to_aoi_grid(da_C.squeeze(drop=True), aoi)
        daily_arrays.append(arr)
        time_coords = [np.datetime64(f"{year:04d}-{month:02d}-01")]

    stacked = np.stack(daily_arrays, axis=0)  # (n_days, H, W)
    nan_mask = ~np.isfinite(stacked)
    stacked[nan_mask] = ERA5_NODATA

    h, w = aoi.cells_per_side()
    assert stacked.shape[1:] == (h, w), (
        f"stacked shape {stacked.shape[1:]} != AOI grid {(h, w)}"
    )

    out_da = xr.DataArray(
        stacked.astype(np.float32),
        dims=("time", "y", "x"),
        coords={"time": time_coords},
        attrs={
            "long_name": "ERA5-Land 2m temperature (daily mean)",
            "units": "degC",
            "source": f"ERA5-Land daily stats {ERA5_VARIABLE} {ERA5_DAILY_STATISTIC}",
            "aoi_slug": aoi.slug,
            "year": year,
            "month": month,
            "nodata": ERA5_NODATA,
        },
    )
    out_da.rio.write_crs(aoi.crs_obj, inplace=True)
    return out_da


def load_era5_water_temp(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load ERA5-Land daily 2m temperature in °C for year(s) × month(s).

    Args:
        aoi: the AOI.
        years: sequence of years to load.
        months: sequence of 1-indexed months. None = all 12.
        cache_dir: optional local cache for downloaded NetCDFs.

    Returns:
        xr.DataArray with dims (time, y, x), dtype float32, CRS = aoi.crs.
        Values in degrees Celsius. ``-9999.0`` for NoData.
    """
    if months is None:
        months = list(range(1, 13))

    cdir = cache_dir if cache_dir is not None else _default_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)

    all_arrays: list[xr.DataArray] = []

    for year in sorted(years):
        for month in sorted(months):
            if not (1 <= month <= 12):
                raise ValueError(f"month must be in 1..12; got {month}")
            if year < 1950:
                raise ValueError(f"ERA5 starts in 1950; got year={year}")
            da = _load_era5_water_temp_single(aoi, year, month, cdir)
            all_arrays.append(da)

    if len(all_arrays) == 1:
        return all_arrays[0]

    merged = xr.concat(all_arrays, dim="time")
    merged.attrs.update({
        "long_name": "ERA5-Land 2m temperature (daily mean)",
        "units": "degC",
        "source": f"ERA5-Land daily stats {ERA5_VARIABLE} {ERA5_DAILY_STATISTIC}",
        "aoi_slug": aoi.slug,
        "nodata": ERA5_NODATA,
    })
    merged.rio.write_crs(aoi.crs_obj, inplace=True)
    return merged


# -- ERA5 100m wind (M7.6 Phase 2: 6-hourly windborne migration) --

ERA5_WIND_DATASET: str = "reanalysis-era5-single-levels"
ERA5_WIND_VARIABLES: list[str] = [
    "100m_u_component_of_wind",
    "100m_v_component_of_wind",
]
ERA5_WIND_TIMES: list[str] = ["00:00", "06:00", "12:00", "18:00"]
ERA5_WIND_GHANA_AOI: list[float] = [11.5, -3.5, 4.5, 1.5]  # [W, S, E, N]

# Migration season months per year (monsoon Jul-Oct + Harmattan Dec-Mar).
MIGRATION_SEASON_MONTHS: dict[int, list[str]] = {
    2024: ["07", "08", "09", "10", "12"],
    2025: ["01", "02", "03"],
}

ALL_MONTHS: list[str] = [f"{m:02d}" for m in range(1, 13)]


def _download_era5_wind(
    years: Sequence[int],
    *,
    months: Sequence[int] | None = None,
    cache_dir: pathlib.Path | None = None,
) -> xr.Dataset:
    """Download ERA5 6-hourly 100m wind, year(s) × month(s).

    Downloads ``100m_u_component_of_wind`` and ``100m_v_component_of_wind``
    from ``reanalysis-era5-single-levels`` at 6-hourly resolution
    (00/06/12/18 UTC). One CDS request per (year, month) pair, then
    merges all into a single Dataset sorted by time.

    Args:
        years: sequence of years to download.
        months: sequence of 1-indexed months. None = all 12.
        cache_dir: optional per-month cache directory.

    Returns:
        ``xr.Dataset`` with merged 6-hourly wind data.

    Raises:
        RuntimeError: if CDS auth is missing.
        ValueError: if ``years`` is empty.
    """
    if not years:
        raise ValueError("years must not be empty")
    if months is None:
        months_int = list(range(1, 13))
    else:
        months_int = list(months)

    import cdsapi

    try:
        client = cdsapi.Client()
    except Exception as e:
        raise RuntimeError(
            "ERA5 wind requires CDS auth. Configure ~/.cdsapirc or "
            "CDSAPI_URL/KEY env vars. See op-m1-3a-data-layer-auth for "
            f"details. (cdsapi raised: {e})"
        ) from e

    cdir = cache_dir if cache_dir is not None else _default_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)

    monthly_files: list[str] = []
    for year in sorted(years):
        for m_int in sorted(months_int):
            month_str = f"{m_int:02d}"
            n_days = calendar.monthrange(year, m_int)[1]
            days = [f"{d:02d}" for d in range(1, n_days + 1)]

            target = cdir / f"era5_wind_6h_{year}_{month_str}.nc"
            if not target.exists():
                client.retrieve(
                    ERA5_WIND_DATASET,
                    {
                        "product_type": "reanalysis",
                        "variable": ERA5_WIND_VARIABLES,
                        "year": str(year),
                        "month": [month_str],
                        "day": days,
                        "time": ERA5_WIND_TIMES,
                        "area": ERA5_WIND_GHANA_AOI,
                        "format": "netcdf",
                    },
                    str(target),
                )
            monthly_files.append(str(target))

    datasets = [xr.open_dataset(f) for f in monthly_files]
    merged = xr.concat(datasets, dim="valid_time").sortby("valid_time")
    for ds in datasets:
        ds.close()

    return merged


def load_era5_wind_6hourly(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,
    cache_dir: pathlib.Path | None = None,
) -> xr.Dataset:
    """Load-or-download ERA5 6-hourly 100m wind data.

    Args:
        aoi: AOI object (used for grid reprojection).
        years: sequence of years.
        months: sequence of 1-indexed months. None = all 12.
        cache_dir: cache directory. Default ``~/.cache/mal_commonlib/era5``.

    Returns:
        ``xr.Dataset`` with merged 6-hourly wind data.
    """
    if not years:
        raise ValueError("years must not be empty")

    cdir = cache_dir or _default_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    year_str = "_".join(str(y) for y in sorted(years))
    merged_path = cdir / f"wind_6hourly_{year_str}.nc"

    if merged_path.exists() and merged_path.stat().st_size > 0:
        return xr.open_dataset(merged_path)

    ds = _download_era5_wind(years, months=months, cache_dir=cache_dir)
    ds.to_netcdf(merged_path)
    return ds


DOWNLOADER = {
    "name": "era5",
    "description": "ERA5 reanalysis: temperature, wind, humidity",
    "requires_auth": ["cds"],
    "is_time_series": True,
    "outputs": {
        "temp_suitability": load_era5_temp_suitability,
        "water_temp": load_era5_water_temp,
        "wind_6hourly": load_era5_wind_6hourly,
    },
    "manifest_keys": {
        "temp_suitability": "era5_temp",
        "water_temp": "era5_water_temp",
        "wind_6hourly": "wind",
    },
}

__all__ = [
    "DOWNLOADER",
    "load_era5_temp_suitability",
    "load_era5_water_temp",
    "load_era5_wind_6hourly",
    "sharpe_demichele_growth",
    "T_OPT",
    "T_HALF_WIDTH",
    "ERA5_NODATA",
    "ERA5_DATASET",
    "ERA5_VARIABLE",
    "ERA5_WIND_DATASET",
    "ERA5_WIND_VARIABLES",
    "ERA5_WIND_TIMES",
    "ERA5_WIND_GHANA_AOI",
    "MIGRATION_SEASON_MONTHS",
    "ALL_MONTHS",
]
