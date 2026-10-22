"""ERA5-Land daily statistics loader (contract v3.0, channel: air_temp_daily).

Public surface:
    load_era5_air_temp_daily(aoi, *, years, months=None, cache_dir=None) -> xr.DataArray
    load_era5_wind_6hourly(aoi, *, years, months=None, cache_dir=None) -> xr.Dataset

Source: Copernicus CDS — ``derived-era5-land-daily-statistics`` dataset.
Variable: ``2m_temperature`` (daily mean, K -> daily °C).

Auth:
    ERA5-Land requires CDS API credentials (``~/.cdsapirc`` or
    ``CDSAPI_URL``/``CDSAPI_KEY`` env vars). In an env without those, the
    loader raises ``RuntimeError`` with a clear message. See
    ``op-m1-3a-data-layer-auth`` in the project knowledge graph for the
    data-layer auth runbook.

Notes:
    * Contract v3.0 names the channel after what it actually measures:
      near-surface AIR temperature in °C. The retired annual TIF products
      ``temp_suitability`` (Sharpe-DeMichele parabolic transform) and
      ``water_temp`` (annual mean-TIF mislabelled as a biological water
      temperature) are deleted (plan
      docs/plans/in-process/redesign/01-retirada-hidrologia-dem-escorrentia.md
      §7). Thermal biology (adult survival, aquatic development, EIP) now
      consumes the daily air temperature series directly inside the C++
      engine via the workspace thermal responses — the Bombay-Marchant /
      Lardeaux style habitat model of the previous regime is NOT a loss to
      the redesign; it never used this channel anyway.
    * Output dims: (time, y, x) daily float32 in degrees Celsius.
      NoData: the NoData sentinel. The daily multi-year path is wired through
      ``formats["air_temp_daily"] = "daily"`` in the DOWNLOADER dict (the
      runner writes ONE multi-year daily NC and registers it with period
      metadata).
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
from mal_commonlib.model_constants import model_constant


ERA5_NODATA: float = float(model_constant("ingest", "nodata_sentinel"))
ERA5_DATASET: str = "derived-era5-land-daily-statistics"
ERA5_VARIABLE: str = "2m_temperature"
ERA5_DAILY_STATISTIC: str = "daily_mean"  # daily mean; daily °C contract
ERA5_FREQ: str = "1_hourly"               # CDS frequency for daily-statistics dataset
ERA5_AREA_PAD_DEG: float = 0.5            # CDS area padding (see _cds_request)

# CDS API requests use the long variable name "2m_temperature", but the
# NetCDF files it ships use the short name "t2m". Map long → short so the
# reader can find the variable in the downloaded file.
ERA5_VARIABLE_NETCDF_ALIAS: dict[str, str] = {
    "2m_temperature": "t2m",
}


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
    """Reproject a 2-D DataArray to the AOI's grid; returns float32 (H, W).

    2026-10-20 freeze bug — three defects compounded here:

    1. CDS accepted tiny-area requests ([5.75, 0.05, 5.35, 0.6]) but served
       a near-empty grid (1 of 24 cells finite per day, reproducible via a
       fresh request), while proven-good requests for the same dataset use
       padded areas (e.g. the Ghana-wide 71x51 caches are 100% finite).
       The source grid is 0.1 deg — the AOI must be padded by at least one
       margin so every requested point sits inside grid coverage.
    2. CDS netCDF ships the slice with ``_FillValue = NaN``; GDAL's bilinear
       warper turns every NaN source cell into an expanding nodata fillet,
       so with a sparse-valid source almost the whole target plane came
       back NaN (only a ~6x6 corner survived in the committed env NC).
       NaN nodata is replaced by a finite sentinel BEFORE the warp.
    3. After the warp the target plane is nearest-filled for any remaining
       hole so a broken interior cannot slip into the env NC silently.

    Raises RuntimeError if the source slice is still near-empty — garbage
    source data must fail the download loudly, not survive as a mostly-
    nodata NC that the engine then silently zeros.
    """
    import scipy.ndimage

    v = np.asarray(da.values, dtype=np.float32)
    finite = np.isfinite(v)
    valid_cells = int(finite.sum())
    if valid_cells < 0.5 * v.size:
        raise RuntimeError(
            "ERA5 source slice is near-empty "
            f"({valid_cells} of {v.size} cells finite): CDS served missing "
            "data for the requested area. Retry the download or widen the "
            "request area; a mostly-nodata air temperature plane would "
            "silently freeze the model."
        )
    if valid_cells < v.size:
        missing = ~finite & (v != ERA5_NODATA)
        if missing.any():
            # Nearest-neighbour fill of interior CDS holes before the
            # warp — GDAL's bilinear fillets cannot be trusted on NaN.
            idx = scipy.ndimage.distance_transform_edt(
                missing, return_distances=False, return_indices=True)
            v = v[tuple(idx)]  # NaN holes become the nearest finite value
        da = da.copy(data=v)
        da.rio.write_nodata(ERA5_NODATA, inplace=True)
    da_ = da
    if da_.rio.crs is None:
        da_.rio.write_crs("EPSG:4326", inplace=True)
    ref = _ref_grid_for_aoi(aoi)
    rep = da_.rio.reproject_match(ref, resampling=rasterio.enums.Resampling.bilinear)
    out = np.asarray(rep.values, dtype=np.float32)
    bad = ~np.isfinite(out) | (out == ERA5_NODATA)
    if bad.any():
        idx = scipy.ndimage.distance_transform_edt(
            bad, return_distances=False, return_indices=True)
        out = out[tuple(idx)]
    return out


def _cds_request(year: int, month: int, bbox_wsen: tuple[float, float, float, float]) -> dict:
    """Build a CDS API request for the AOI bbox and (year, month).

    2026-10-20: the CDS request area is PADDED by ERA5_AREA_PAD_DEG.
    Reproduced failure (see _reproject_to_aoi_grid docstring): a request for
    the bare 0.55 deg-wide accra-coastal-test box ([5.75, 0.05, 5.35, 0.6])
    returned a 4x6 source grid with exactly 1 of 24 cells finite per day
    (validated on a fresh request); the same dataset with a padded area
    (Ghana-wide caches, 71x51) is fully finite every day. Padding also keeps
    the bilinear warp off the source edges. The crop below removes the
    padding again once the NC is on the AOI grid.
    """
    import os

    w, s, e, n = bbox_wsen
    pad = float(os.environ.get("ERA5_AREA_PAD_DEG", ERA5_AREA_PAD_DEG))
    return {
        "variable": [ERA5_VARIABLE],
        "daily_statistic": [ERA5_DAILY_STATISTIC],
        "year": [f"{year:04d}"],
        "month": [f"{month:02d}"],
        "day": _days_in_month(year, month),
        "time_zone": "utc+00:00",
        "frequency": [ERA5_FREQ],
        "area": [n + pad, w - pad, s - pad, e + pad],  # CDS API: [N, W, S, E]
    }


# -- public API ----------------------------------------------------------------------


def _load_era5_air_temp_single(
    aoi: AOI,
    year: int,
    month: int,
    cache_dir: pathlib.Path,
) -> xr.DataArray:
    """Load a single (year, month) of ERA5 daily 2 m air temperature for the AOI."""
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


def load_era5_air_temp_daily(
    aoi: AOI,
    *,
    years: Sequence[int],
    months: Sequence[int] | None = None,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load ERA5-Land daily 2 m air temperature in °C for year(s) × month(s).

    Args:
        aoi: the AOI.
        years: sequence of years to load.
        months: sequence of 1-indexed months. None = all 12.
        cache_dir: optional local cache for downloaded NetCDFs.

    Returns:
        xr.DataArray with dims (time, y, x), dtype float32, CRS = aoi.crs.
        Values in degrees Celsius. ``NODATA_SENTINEL()`` for NoData.
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
            da = _load_era5_air_temp_single(aoi, year, month, cdir)
            all_arrays.append(da)

    if len(all_arrays) == 1:
        # Contract var name: the daily channel the ABM env NC consumes.
        return all_arrays[0].rename("air_temp_c")

    merged = xr.concat(all_arrays, dim="time").rename("air_temp_c")
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
    "description": "ERA5 reanalysis: daily air temperature, wind",
    "requires_auth": ["cds"],
    "license": "Copernicus-Cite",
    "attribution": (
        "Contains modified Copernicus Climate Change Service information "
        "[Year]. Neither the European Commission nor ECMWF is responsible "
        "for any use that may be made of the Copernicus information or data "
        "it contains. DOI: 10.24381/cds.5d0b5cf0 / 10.24381/cds.f850e93a"
    ),
    "is_time_series": True,
    "formats": {
        "air_temp_daily": "daily",
        "wind_6hourly": "daily",
    },
    "outputs": {
        "air_temp_daily": load_era5_air_temp_daily,
        "wind_6hourly": load_era5_wind_6hourly,
    },
    "manifest_keys": {
        "air_temp_daily": "era5_air_temp_daily",
        "wind_6hourly": "wind",
    },
    "required_for_abm": {
        "air_temp_daily": True,
        "wind_6hourly": False,
    },
}

__all__ = [
    "DOWNLOADER",
    "load_era5_air_temp_daily",
    "load_era5_wind_6hourly",
    "ERA5_NODATA",
    "ERA5_DATASET",
    "ERA5_VARIABLE",
    "ERA5_DAILY_STATISTIC",
    "ERA5_VARIABLE_NETCDF_ALIAS",
    "ERA5_WIND_DATASET",
    "ERA5_WIND_VARIABLES",
    "ERA5_WIND_TIMES",
    "ERA5_WIND_GHANA_AOI",
    "MIGRATION_SEASON_MONTHS",
    "ALL_MONTHS",
]
