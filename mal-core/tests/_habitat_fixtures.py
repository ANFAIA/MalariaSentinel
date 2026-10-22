"""Shared synthetic-input fixtures for the contract-v3.0 ingest tests
(daily env NC, habitat static planes — used by test_smap, test_m12_*)."""
from __future__ import annotations

import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import from_origin


def write_tif(path, values, nodata=-9999.0):
    values = np.asarray(values, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
        nodata=nodata,
    ) as dst:
        dst.write(values, 1)


def write_rainfall_nc(path, times, h=2, w=2, base=1.0):
    rainfall = np.full((len(times), h, w), base, dtype=np.float32)
    xr.Dataset(
        {"rainfall": (("time", "y", "x"), rainfall)},
        coords={"time": times, "y": np.linspace(0.0, 1.0, h),
                "x": np.linspace(0.0, 1.0, w)},
    ).to_netcdf(path)


def write_air_temp_daily_nc(path, times, h=2, w=2, base_c=25.0):
    """ERA5 daily air temperature in °C with a real per-day time axis."""
    vals = np.full((len(times), h, w), base_c, dtype=np.float32)
    xr.Dataset(
        {"air_temp_c": (("time", "y", "x"), vals)},
        coords={"time": times.astype("datetime64[D]"),
                "y": np.linspace(0.0, 1.0, h),
                "x": np.linspace(0.0, 1.0, w)},
    ).to_netcdf(path)


def write_jrc_features_nc(path, jrc_persistent, h=2, w=2):
    jrc_persistent = np.atleast_2d(np.asarray(jrc_persistent, dtype=np.float32))
    h2, w2 = jrc_persistent.shape
    xr.Dataset(
        {"jrc_persistent": (("y", "x"), jrc_persistent)},
        coords={"y": np.linspace(0.0, 1.0, h2),
                "x": np.linspace(0.0, 1.0, w2)},
        attrs={"contract": "habitat-v3.0-statics"},
    ).to_netcdf(path)


def write_dw_fractions_nc(path, h=2, w=2, built=0.1, wetland=0.1,
                          openp=0.4, crop=0.2):
    """Uniform four-plane Dynamic World fraction NC."""
    shape = (h, w)
    xr.Dataset(
        {
            "lc_built": (("y", "x"), np.full(shape, built, dtype=np.float32)),
            "lc_wetland": (("y", "x"), np.full(shape, wetland, dtype=np.float32)),
            "lc_open_plus_water": (
                ("y", "x"), np.full(shape, openp, dtype=np.float32)),
            "lc_crop": (("y", "x"), np.full(shape, crop, dtype=np.float32)),
        },
        coords={"y": np.linspace(0.0, 1.0, h),
                "x": np.linspace(0.0, 1.0, w)},
        attrs={"contract": "habitat-v3.0-statics"},
    ).to_netcdf(path)


def write_dw_fractions_nc_grid(path, grid):
    """Per-cell Dynamic World fraction NC, `grid` = dict of (h, w) arrays."""
    shape = tuple(np.asarray(grid["lc_built"]).shape)
    xr.Dataset(
        {k: (("y", "x"), np.asarray(v, dtype=np.float32))
         for k, v in grid.items()},
        coords={"y": np.linspace(0.0, 1.0, shape[0]),
                "x": np.linspace(0.0, 1.0, shape[1])},
        attrs={"contract": "habitat-v3.0-statics"},
    ).to_netcdf(path)


def write_land_mask_tif(path, values):
    write_tif(path, values)
