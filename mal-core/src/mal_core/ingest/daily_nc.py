"""Daily env NC builder — produces the (time, y, x) NetCDF the C++ ABM reads.

Combines:
  - CHIRPS daily rainfall (mm/day, dims: time, y, x)
  - JRC GSW water occurrence (static, normalized to [0, 1]) -> water_frac
  - ERA5 water temperature (deg C) -> water_temp_c
  - MODIS NDVI (vegetation index, clipped to [0, 1]) -> ndvi

Optional M12 enrichment (when TIF files are present in data_dir):
  - HydroLAKES permanent water mask ({aoi}_permanent_lakes.tif) -> merged
    into water_frac via np.maximum(JRC_GSW, permanent_water)
  - ESA WorldCover wetland mask ({aoi}_wc_wetland.tif) -> diagnostic
    variable (wetland contribution to water_frac is commented-out by default)

Static layers are broadcast to every day (the ABM's daily slice has the same
spatial climate each day; only rainfall changes per day in this version).

Output contract: docs/specs/data/spec.md §6.3, variables matching
mal-core/src/mal_core/abm/include/mal_abm_fast/climate.hpp:80-86.
"""
from __future__ import annotations

import pathlib
import re
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
    year_match = re.search(r"_(20\d{2})(?:_|\.)", rain_file.name)
    data_year = year_match.group(1) if year_match else "2024"
    water_temp_file = water_temp_file or (data_dir / f"{aoi}_water_temp_{data_year}.tif")
    ndvi_file = ndvi_file or (data_dir / f"{aoi}_ndvi_{data_year}.tif")

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

    # --- M12 enrichment: compose M12 water datasets into water_frac ---
    # Optional layers from hydrolakes / worldcover loaders.  When present
    # they improve the water_frac estimate; when absent the function falls
    # back to JRC GSW only (backward-compatible).
    permanent_water_mask = None
    wetland_mask = None
    component_masks: dict[str, np.ndarray] = {}

    lakes_file = data_dir / f"{aoi}_permanent_lakes.tif"
    if lakes_file.exists():
        print(f"Loading M12 permanent water mask: {lakes_file}")
        permanent_water_mask = read_static_tif(lakes_file, target_shape)
        permanent_water_mask = np.nan_to_num(permanent_water_mask, nan=0.0)
        permanent_water_mask = np.clip(permanent_water_mask, 0.0, 1.0)
        component_masks["permanent_lakes"] = permanent_water_mask.copy()

    rivers_file = data_dir / f"{aoi}_permanent_rivers.tif"
    if rivers_file.exists():
        rivers = np.clip(np.nan_to_num(read_static_tif(rivers_file, target_shape), nan=0.0), 0.0, 1.0)
        component_masks["permanent_rivers"] = rivers.copy()
        permanent_water_mask = rivers if permanent_water_mask is None else np.maximum(permanent_water_mask, rivers)

    worldcover_water_file = data_dir / f"{aoi}_wc_permanent_water.tif"
    if worldcover_water_file.exists():
        wc_water = np.clip(np.nan_to_num(read_static_tif(worldcover_water_file, target_shape), nan=0.0), 0.0, 1.0)
        component_masks["worldcover_permanent_water"] = wc_water.copy()
        permanent_water_mask = wc_water if permanent_water_mask is None else np.maximum(permanent_water_mask, wc_water)

    wetland_file = data_dir / f"{aoi}_wc_wetland.tif"
    if wetland_file.exists():
        print(f"Loading M12 wetland mask: {wetland_file}")
        wetland_mask = read_static_tif(wetland_file, target_shape)
        wetland_mask = np.nan_to_num(wetland_mask, nan=0.0)
        wetland_mask = np.clip(wetland_mask, 0.0, 1.0)

    # Merge: permanent water always has water_frac = 1.0
    if permanent_water_mask is not None:
        water_frac_static = np.maximum(water_frac_static, permanent_water_mask)

    # Optionally add wetland contribution (uncomment to enable)
    # if wetland_mask is not None:
    #     water_frac_static = np.clip(water_frac_static + 0.3 * wetland_mask, 0.0, 1.0)

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
                           {"long_name": "Enriched water fraction (JRC GSW + M12 permanent water)",
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
            "generator_version": "m2-daily-0.5.0",
            "m12_enriched": int(permanent_water_mask is not None or wetland_mask is not None),
        },
    )
    for name, component in component_masks.items():
        ds[f"m12_{name}"] = (
            ["time", "y", "x"], np.broadcast_to(component, (n_days, h, w)).copy(),
            {"long_name": f"M12 {name} mask", "units": "1"},
        )

    # Optional diagnostic variables (C++ reader ignores them via GDAL)
    if permanent_water_mask is not None:
        pw_broadcast = np.broadcast_to(permanent_water_mask, (n_days, h, w)).copy()
        ds["permanent_water_mask"] = (
            ["time", "y", "x"], pw_broadcast,
            {"long_name": "Permanent water mask (JRC GSW ≥95%)", "units": "1"},
        )


    if wetland_mask is not None:
        wl_broadcast = np.broadcast_to(wetland_mask, (n_days, h, w)).copy()
        ds["wetland_mask"] = (
            ["time", "y", "x"], wl_broadcast,
            {"long_name": "Wetland mask (ESA WorldCover class 90)", "units": "1"},
        )

    # Core variables are always written with zlib; diagnostic vars too
    encoding_vars = ["water_frac", "rainfall", "water_temp_c", "ndvi"]
    if permanent_water_mask is not None:
        encoding_vars.append("permanent_water_mask")
    if wetland_mask is not None:
        encoding_vars.append("wetland_mask")

    encoding = {v: {"dtype": "float32", "zlib": True, "complevel": 4}
                for v in encoding_vars}

    years_in_data = np.unique(times.astype("datetime64[Y]")).astype(int) + 1970
    output_path = output_dir / f"{aoi}_regional_{years_in_data.min()}_{years_in_data.max()}_env.nc"
    print(f"Writing: {output_path}")
    ds.to_netcdf(output_path, encoding=encoding)

    print(
        f"\n=== SUMMARY ===\n"
        f"  water_frac: [{water_frac.min():.4f}, {water_frac.max():.4f}], "
        f"viable cells (>0.05): {n_viable}\n"
        f"  M12 enrichment: permanent_water={'yes' if permanent_water_mask is not None else 'no'}, "
        f"wetland={'yes' if wetland_mask is not None else 'no'}\n"
        f"  rainfall: [{rainfall.min():.1f}, {rainfall.max():.1f}], "
        f"nodata replaced: {nodata_count}\n"
        f"  water_temp: [{water_temp_c.min():.1f}, {water_temp_c.max():.1f}]\n"
        f"  ndvi: [{ndvi.min():.2f}, {ndvi.max():.2f}]"
    )

    # Manifest variable list: core ABM variables always present; M12 diagnostics
    # are optional (C++ reader ignores them, but they're useful for analysis).
    variables = ["water_frac", "rainfall", "water_temp_c", "ndvi"]
    if permanent_water_mask is not None:
        variables.append("permanent_water_mask")
    if wetland_mask is not None:
        variables.append("wetland_mask")

    return {
        "env_path": str(output_path),
        "format": "nc",
        "aoi_slug": aoi,
        "n_days": n_days,
        "n_viable_cells": n_viable,
        "grid": f"{h}x{w}",
        "variables": variables,
        "m12_enriched": permanent_water_mask is not None or wetland_mask is not None,
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
