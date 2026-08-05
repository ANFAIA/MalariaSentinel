"""Daily env NC builder — produces the (time, y, x) NetCDF the C++ ABM reads.

Combines:
  - CHIRPS daily rainfall (mm/day, dims: time, y, x)
  - JRC GSW water occurrence (static, normalized to [0, 1]) -> water_frac
  - ERA5 water temperature (deg C) -> water_temp_c
  - MODIS NDVI (vegetation index, clipped to [0, 1]) -> ndvi

Static layers are broadcast to every day (the ABM's daily slice has the same
spatial climate each day; only rainfall changes per day in this version).

Output contract: docs/specs/data/spec.md §6.3, variables matching
mal-core/src/mal_core/abm/include/mal_abm_fast/climate.hpp:80-86.
"""
from __future__ import annotations

import pathlib
from typing import Tuple

import numpy as np
import rasterio
import xarray as xr

NODATA_SENTINEL = -9999.0
WATER_FRAC_VIABILITY_THRESHOLD = 0.05


def read_static_tif(
    path: pathlib.Path, target_shape: Tuple[int, int]
) -> np.ndarray:
    """Read a single-band TIF and return (H, W) float32, nodata -> NaN.

    Resamples bilinearly to ``target_shape`` if the source grid differs.
    """
    with rasterio.open(path) as src:
        nodata = src.nodata
        if (src.height, src.width) == target_shape:
            data = src.read(1).astype(np.float32)
        else:
            from rasterio.enums import Resampling
            data = src.read(
                1,
                out_shape=target_shape,
                resampling=Resampling.bilinear,
            ).astype(np.float32)
        if nodata is not None:
            mask = np.isclose(data, nodata, atol=1.0) | (data == NODATA_SENTINEL)
            data[mask] = np.nan
        return data


def build_daily_env_nc(
    aoi: str,
    data_dir: pathlib.Path,
    output_dir: pathlib.Path | None = None,
    rainfall_file: pathlib.Path | None = None,
    water_frac_file: pathlib.Path | None = None,
    water_temp_file: pathlib.Path | None = None,
    ndvi_file: pathlib.Path | None = None,
) -> dict:
    """Build the daily env NC for an AOI. Returns manifest-ready dict.

    Args:
        aoi: AOI slug (used for output filename and manifest registration).
        data_dir: directory containing the raw input files.
        output_dir: where to write the NC (default: data_dir).
        rainfall_file, water_frac_file, water_temp_file, ndvi_file:
            override input paths (default: conventional filenames in data_dir).

    Returns:
        dict with 'env_path' (str), 'format' ('nc'), 'aoi_slug', 'n_days',
        'n_viable_cells', and 'grid'.
    """
    data_dir = pathlib.Path(data_dir)
    output_dir = pathlib.Path(output_dir) if output_dir else data_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rain_file = rainfall_file or (
        data_dir / f"{aoi}_rainfall_daily_2024_2025_daily.nc"
        if (data_dir / f"{aoi}_rainfall_daily_2024_2025_daily.nc").exists()
        else _find_chirps_daily(data_dir)
    )
    water_frac_file = water_frac_file or (data_dir / f"{aoi}_water_occurrence.tif")
    water_temp_file = water_temp_file or (data_dir / f"{aoi}_water_temp_2024.tif")
    ndvi_file = ndvi_file or (data_dir / f"{aoi}_ndvi_2024.tif")

    for label, p in [
        ("rainfall", rain_file),
        ("water_frac", water_frac_file),
        ("water_temp", water_temp_file),
        ("ndvi", ndvi_file),
    ]:
        if not p.exists():
            raise FileNotFoundError(
                f"{label} input not found: {p}. "
                f"Run: malariasim download --aoi {aoi} --datasets <required>"
            )

    print(f"Reading rainfall: {rain_file}")
    rain_ds = xr.open_dataset(rain_file)
    rainfall_raw = rain_ds.rainfall.values
    times = rain_ds.time.values
    y = rain_ds.y.values
    x = rain_ds.x.values
    n_days, h, w = rainfall_raw.shape
    target_shape = (h, w)

    # Mask rainfall nodata (-9999) -> 0.0. NaN rainfall propagates through
    # the C++ climate engine and breaks aquatic dynamics; 0.0 is the safe
    # replacement (treats nodata as "no rain that day").
    rainfall = rainfall_raw.astype(np.float32)
    nodata_mask = rainfall_raw == NODATA_SENTINEL
    nodata_count = int(nodata_mask.sum())
    rainfall[nodata_mask] = 0.0
    rainfall[rainfall < 0] = 0.0

    # JRC GSW water occurrence -> water_frac (static, broadcast to all days)
    print(f"Reading water_frac: {water_frac_file}")
    water_frac_static = read_static_tif(water_frac_file, target_shape)
    if np.nanmax(water_frac_static) > 1.0:
        water_frac_static = water_frac_static / 100.0
    water_frac_static = np.nan_to_num(water_frac_static, nan=0.0)
    water_frac = np.broadcast_to(water_frac_static, (n_days, h, w)).copy()
    n_viable = int((water_frac_static > WATER_FRAC_VIABILITY_THRESHOLD).sum())
    if n_viable == 0:
        raise RuntimeError(
            f"CRITICAL: 0 viable habitat patches for AOI '{aoi}'! "
            f"water_frac is all <= {WATER_FRAC_VIABILITY_THRESHOLD}. "
            f"Check {water_frac_file} contains real JRC GSW data."
        )

    # ERA5 water temperature -> water_temp_c
    print(f"Reading water_temp: {water_temp_file}")
    water_temp_static = read_static_tif(water_temp_file, target_shape)
    water_temp_static = np.nan_to_num(water_temp_static, nan=25.0)
    water_temp_c = np.broadcast_to(water_temp_static, (n_days, h, w)).copy()

    # MODIS NDVI -> ndvi
    print(f"Reading ndvi: {ndvi_file}")
    ndvi_static = read_static_tif(ndvi_file, target_shape)
    ndvi_static = np.nan_to_num(ndvi_static, nan=0.5)
    ndvi_static = np.clip(ndvi_static, 0.0, 1.0)
    ndvi = np.broadcast_to(ndvi_static, (n_days, h, w)).copy()

    ds = xr.Dataset(
        {
            "water_frac": (["time", "y", "x"], water_frac,
                           {"long_name": "JRC GSW open water fraction",
                            "units": "1"}),
            "rainfall": (["time", "y", "x"], rainfall,
                         {"long_name": "CHIRPS v2.0 daily precipitation",
                          "units": "mm/day"}),
            "water_temp_c": (["time", "y", "x"], water_temp_c,
                             {"long_name": "ERA5-Land 2m temperature (daily mean)",
                              "units": "degC"}),
            "ndvi": (["time", "y", "x"], ndvi,
                     {"long_name": "MODIS NDVI", "units": "1"}),
        },
        coords={"time": times, "y": y, "x": x},
        attrs={
            "Conventions": "CF-1.8",
            "title": f"MalariaSentinel daily env tensor — {aoi}",
            "aoi_slug": aoi,
            "scale": "regional",
            "contract_version": "2.0",
            "generator_version": "m2-daily-0.4.0",
        },
    )

    encoding = {v: {"dtype": "float32", "zlib": True, "complevel": 4}
                for v in ["water_frac", "rainfall", "water_temp_c", "ndvi"]}

    output_path = output_dir / f"{aoi}_regional_2024_2025_env.nc"
    print(f"Writing: {output_path}")
    ds.to_netcdf(output_path, encoding=encoding)

    print(
        f"\n=== SUMMARY ===\n"
        f"  water_frac: [{water_frac.min():.4f}, {water_frac.max():.4f}], "
        f"viable cells (>0.05): {n_viable}\n"
        f"  rainfall: [{rainfall.min():.1f}, {rainfall.max():.1f}], "
        f"nodata replaced: {nodata_count}\n"
        f"  water_temp: [{water_temp_c.min():.1f}, {water_temp_c.max():.1f}]\n"
        f"  ndvi: [{ndvi.min():.2f}, {ndvi.max():.2f}]"
    )

    return {
        "env_path": str(output_path),
        "format": "nc",
        "aoi_slug": aoi,
        "n_days": n_days,
        "n_viable_cells": n_viable,
        "grid": f"{h}x{w}",
        "variables": ["water_frac", "rainfall", "water_temp_c", "ndvi"],
    }


def _find_chirps_daily(data_dir: pathlib.Path) -> pathlib.Path:
    """Locate the CHIRPS daily NC by glob fallback."""
    candidates = sorted(data_dir.glob("*rainfall_daily*.nc"))
    if not candidates:
        raise FileNotFoundError(
            f"No CHIRPS daily rainfall NC found in {data_dir}. "
            f"Run: malariasim download --aoi <slug> --datasets chirps "
            f"--outputs rainfall_daily --years 2024 2025"
        )
    return candidates[0]
