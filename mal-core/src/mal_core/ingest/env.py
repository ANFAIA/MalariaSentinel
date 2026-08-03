"""Ingest stage — build the env tensor + habitat patches for an AOI.

Extracted from mal-execution/scripts/build_environment.py.
Core logic preserved; CLI layer removed.
"""
# MIGRATION NOTE (M13 Phase 4):
# The legacy `output_format='nc'` path in build_env_tensor() is deprecated.
# Daily NC files are now produced by the runner:
#   malariasim download --outputs rainfall_daily --years 2024 2025
# See docs/plans/in-process/m13-daily-env-nc.md §3.5.
# Legacy _write_env_nc() function has been removed.
from __future__ import annotations

import json
import pathlib
import warnings
from typing import Mapping

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI, Scale
from mal_commonlib.data.loaders.chirps import load_chirps_rainfall
from mal_commonlib.data.loaders.dem import load_merit_dem
from mal_commonlib.data.loaders.era5 import load_era5_temp_suitability
from mal_commonlib.data.loaders.jrc_gsw import load_jrc_gsw_water_frac
from mal_commonlib.data.loaders.modis import load_modis_ndvi
from mal_commonlib.terrain.twi import compute_twi

from ._shared import (
    NODATA_SENTINEL,
    empty_channel,
    register_dataset,
    safe_load,
)

# Per docs/abm-output-contract.md §2: four band names in order.
ENV_BAND_NAMES: tuple[str, ...] = (
    "water_frac",
    "rainfall",
    "temp_suitability",
    "ndvi",
)
GENERATOR_VERSION: str = "m1-thin-0.1.0"
CONTRACT_VERSION: str = "1.0"


# -- helpers ----------------------------------------------------------------


def _stack_env_channels(
    channels: Mapping[str, xr.DataArray],
    aoi: AOI,
) -> xr.DataArray:
    """Stack 4 named channels into a (band=4, y, x) array."""
    missing = [name for name in ENV_BAND_NAMES if name not in channels]
    if missing:
        raise KeyError(f"channels missing: {missing}; got {list(channels)}")

    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)

    arrs: list[np.ndarray] = []
    for name in ENV_BAND_NAMES:
        da = channels[name]
        if da.rio.crs is None:
            da = da.rio.write_crs(aoi.crs_obj, inplace=True)
        if da.shape != (h, w):
            raise ValueError(
                f"channel {name!r} has shape {da.shape}; expected {(h, w)}"
            )
        arrs.append(np.asarray(da.values, dtype=np.float32))

    stacked = np.stack(arrs, axis=0).astype(np.float32)
    assert stacked.shape == (4, h, w)

    out = xr.DataArray(
        stacked,
        dims=("band", "y", "x"),
        coords={"band": list(ENV_BAND_NAMES)},
        attrs={
            "long_name": "env tensor (4 channels)",
            "band_names": list(ENV_BAND_NAMES),
            "aoi_slug": aoi.slug,
            "nodata": NODATA_SENTINEL,
        },
    )
    out.rio.write_crs(aoi.crs_obj, inplace=True)
    out.rio.write_transform(transform, inplace=True)
    return out


def _write_env_cog(
    path: pathlib.Path,
    env: xr.DataArray,
    aoi: AOI,
    year: int,
    month: int,
) -> pathlib.Path:
    """Write the env tensor as a COG GeoTIFF + sidecar JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)
    arr = np.asarray(env.values, dtype=np.float32)
    assert arr.shape == (4, h, w)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 4,
        "height": h,
        "width": w,
        "crs": aoi.crs,
        "transform": transform,
        "nodata": NODATA_SENTINEL,
        "tiled": True,
        "compress": "deflate",
        "blockxsize": 128,
        "blockysize": 128,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr)
        for i, name in enumerate(ENV_BAND_NAMES, start=1):
            dst.set_band_description(i, name)

    sidecar = {
        "crs": aoi.crs,
        "transform": [float(x) for x in transform[:6]],
        "aoi_slug": aoi.slug,
        "scale": aoi.scale.value,
        "year": int(year),
        "month": int(month),
        "generator_version": GENERATOR_VERSION,
        "abm_params_hash": "sha256:pending",
        "contract_version": CONTRACT_VERSION,
        "band_names": list(ENV_BAND_NAMES),
        "nodata": NODATA_SENTINEL,
        "shape": list(arr.shape),
    }
    sidecar_path = path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    return path


def _write_habitat_patches_gpkg(
    path: pathlib.Path,
    dem: xr.DataArray,
    water_frac: xr.DataArray,
    aoi: AOI,
    *,
    twi_threshold: float = 8.0,
) -> pathlib.Path:
    """Detect pluvial pool patches from TWI + water_frac, write a GeoPackage."""
    twi = compute_twi(dem, cell_size_m=float(aoi.resolution_m))

    twi_arr = np.asarray(twi.values, dtype=np.float32)
    water_arr = np.asarray(water_frac.values, dtype=np.float32)
    h, w = aoi.cells_per_side()
    assert twi_arr.shape == (h, w)
    assert water_arr.shape == (h, w)

    candidate_mask = (twi_arr > twi_threshold) & (water_arr > 0.0) & np.isfinite(twi_arr)
    rows, cols = np.where(candidate_mask)

    transform = from_bounds(*aoi.bbox, w, h)
    xs = transform.c + (cols + 0.5) * transform.a
    ys = transform.f + (rows + 0.5) * transform.e

    gdf = gpd.GeoDataFrame(
        {
            "twi_value": twi_arr[rows, cols].astype(np.float64),
            "water_frac_value": water_arr[rows, cols].astype(np.float64),
            "row": rows.astype(np.int32),
            "col": cols.astype(np.int32),
            "aoi_slug": aoi.slug,
        },
        geometry=[Point(float(x), float(y)) for x, y in zip(xs, ys)],
        crs=aoi.crs,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG")
    return path


# -- public API -------------------------------------------------------------


def build_env_tensor(
    aoi,
    year: int,
    month: int,
    output_dir: pathlib.Path,
    *,
    scale: str = "regional",
    skip_era5: bool = False,
    skip_modis: bool = False,
    skip_jrc_gsw: bool = False,
    output_format: str = "tif",
    name: str | None = None,
    twi_threshold: float = 8.0,
) -> dict:
    """Build the env tensor + habitat patches for an AOI + month.

    Args:
        aoi: the AOI object or a string slug.
        year: year (e.g. 2024).
        month: month 1-12.
        output_dir: directory for outputs.
        scale: multi-scale level.
        skip_era5: skip ERA5 (channel becomes NoData).
        skip_modis: skip MODIS (channel becomes NoData).
        skip_jrc_gsw: skip JRC GSW (water_frac becomes NoData).
        output_format: 'tif' (COG) or 'nc' (daily NetCDF).
        name: optional human-readable AOI name.
        twi_threshold: TWI threshold for habitat patch detection.

    Returns:
        dict with 'env_path', 'habitat_path', and other metadata.
    """
    if output_format == "nc":
        warnings.warn(
            "output_format='nc' is deprecated and will be removed in M14. "
            "Use 'malariasim download --outputs rainfall_daily --years YYYY YYYY' "
            "to produce daily NC files via the runner. "
            "See docs/plans/in-process/m13-daily-env-nc.md §3.5.",
            DeprecationWarning,
            stacklevel=2,
        )

    if isinstance(aoi, str):
        aoi = AOI.from_slug(aoi)
    if isinstance(scale, str):
        scale = Scale(scale)
    h, w = aoi.cells_per_side()
    suffix = f"{aoi.slug}_{aoi.scale.value}_{year:04d}_{month:02d}"
    ext = "tif"
    env_path = output_dir / f"{suffix}_env.{ext}"
    habitat_path = output_dir / f"{suffix}_habitat_patches.gpkg"

    results: dict = {
        "aoi_slug": aoi.slug,
        "scale": aoi.scale.value,
        "grid": f"{h}x{w}",
        "year": year,
        "month": month,
        "format": output_format,
    }

    # Load water_frac
    skip_water = bool(skip_jrc_gsw)
    if skip_water:
        water_frac = empty_channel(aoi, value=NODATA_SENTINEL, band_name="water_frac")
    else:
        water_frac = safe_load(
            load_jrc_gsw_water_frac, aoi, "water_frac", year=2021, month=month,
        )

    # COG/TIF path
    if skip_era5:
        temp_suitability = empty_channel(aoi, value=NODATA_SENTINEL, band_name="temp_suitability")
    else:
        temp_suitability = safe_load(
            load_era5_temp_suitability, aoi, "temp_suitability",
            year=year, month=month,
        )

    rainfall = safe_load(
        load_chirps_rainfall, aoi, "rainfall", year=year, month=month,
    )

    if skip_modis:
        ndvi = empty_channel(aoi, value=NODATA_SENTINEL, band_name="ndvi")
    else:
        ndvi = safe_load(
            load_modis_ndvi, aoi, "ndvi", year=year, month=month,
        )

    env = _stack_env_channels(
        {
            "water_frac": water_frac,
            "rainfall": rainfall,
            "temp_suitability": temp_suitability,
            "ndvi": ndvi,
        },
        aoi,
    )
    _write_env_cog(env_path, env, aoi, year, month)
    results["env_path"] = str(env_path)

    dem = safe_load(load_merit_dem, aoi, "elevation", year=year, month=month)

    _write_habitat_patches_gpkg(
        habitat_path, dem, water_frac, aoi, twi_threshold=twi_threshold,
    )
    results["habitat_path"] = str(habitat_path)

    # Register in manifest
    register_dataset(
        aoi.slug, "env", year,
        str(env_path.name),
        type="time-series",
        variables=list(ENV_BAND_NAMES),
        format=ext,
    )
    register_dataset(
        aoi.slug, "habitat", year,
        str(habitat_path.name),
        type="time-series",
    )

    return results
