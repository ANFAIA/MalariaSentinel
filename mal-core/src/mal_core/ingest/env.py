"""Ingest stage - build the env tensor + habitat patches for an AOI.

Extracted from mal-execution/scripts/build_environment.py.
Core logic preserved; CLI layer removed.
"""
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

# Per docs/abm-output-contract.md S2: four band names in order.
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
    permanent_mask: xr.DataArray | None = None,
    open_ocean_mask: xr.DataArray | None = None,
) -> pathlib.Path:
    """Detect pluvial pool patches from TWI + water_frac, write a GeoPackage.

    Args:
        open_ocean_mask: optional (H, W) binary mask where 1 = open ocean
            (NOT inside the buffered GSHHG coastline). When supplied, cells
            classified as permanent water (JRC=1.0) that sit in open ocean
            are excluded entirely — they are surf, ports, or estuaries, not
            aquatic habitat. This prevents the saltwater filter from leaking
            ocean cells into the gpkg when ``water_frac`` is read from the
            raw JRC TIF rather than the filtered NC. See M12-fix 2026-08-26.
    """
    twi = compute_twi(dem, cell_size_m=float(aoi.resolution_m))

    twi_arr = np.asarray(twi.values, dtype=np.float32)
    water_arr = np.asarray(water_frac.values, dtype=np.float32)
    h, w = aoi.cells_per_side()
    assert twi_arr.shape == (h, w)
    assert water_arr.shape == (h, w)
    permanent_arr = (np.asarray(permanent_mask.values, dtype=np.float32)
                     if permanent_mask is not None else np.zeros((h, w), dtype=np.float32))
    assert permanent_arr.shape == (h, w)
    open_ocean_arr = (
        np.asarray(open_ocean_mask.values, dtype=np.float32)
        if open_ocean_mask is not None
        else np.zeros((h, w), dtype=np.float32)
    )
    assert open_ocean_arr.shape == (h, w)

    # Candidate: TWI>8 AND water>0 AND finite TWI AND inside the buffered
    # coastline (i.e. NOT open ocean). Open-ocean cells are excluded
    # regardless of permanence classification — surf, ports, and
    # estuaries are not aquatic habitat, even when JRC sees them as
    # permanent water. See M12-fix 2026-08-26.
    in_open_ocean = open_ocean_arr > 0.5
    candidate_mask = (
        (twi_arr > twi_threshold)
        & (water_arr > 0.0)
        & np.isfinite(twi_arr)
        & ~in_open_ocean
    )
    rows, cols = np.where(candidate_mask)

    transform = from_bounds(*aoi.bbox, w, h)
    xs = transform.c + (cols + 0.5) * transform.a
    ys = transform.f + (rows + 0.5) * transform.e

    gdf = gpd.GeoDataFrame(
        {
            "twi_value": twi_arr[rows, cols].astype(np.float64),
            "water_frac_value": water_arr[rows, cols].astype(np.float64),
            "hab_type": np.where(permanent_arr[rows, cols] > 0.0,
                                  "permanent_water", "pluvial_pool"),
            "is_permanent": (permanent_arr[rows, cols] > 0.0).astype(np.int8),
            "source_layer": np.where(permanent_arr[rows, cols] > 0.0,
                                     "permanent_water_mask", "jrc_gsw"),
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
    output_format: str = "nc",
    name: str | None = None,
    twi_threshold: float = 8.0,
    data_root: pathlib.Path | None = None,
) -> dict:
    """Build the env tensor + habitat patches for an AOI.

    Args:
        aoi: the AOI object or a string slug.
        year: year (e.g. 2024).
        month: month 1-12.
        output_dir: directory for outputs.
        scale: multi-scale level.
        skip_era5: skip ERA5 (channel becomes NoData).
        skip_modis: skip MODIS (channel becomes NoData).
        skip_jrc_gsw: skip JRC GSW (water_frac becomes NoData).
        output_format: 'nc' (default, daily multi-year NetCDF consumed by
            the C++ ABM) or 'tif' (legacy 4-band monthly COG).
        name: optional human-readable AOI name.
        twi_threshold: TWI threshold for habitat patch detection.

    Returns:
        dict with 'env_path', 'habitat_path', and other metadata.
    """
    if isinstance(aoi, str):
        aoi = AOI.from_slug(aoi)

    # NC path: daily multi-year NetCDF (M13+ default). Delegates to the
    # canonical builder in daily_nc.py. This is the input format the C++
    # ABM actually reads via read_env_nc() in env_reader.cpp.
    if output_format == "nc":
        from .daily_nc import build_daily_env_nc
        nc_result = build_daily_env_nc(
            aoi=aoi.slug,
            data_dir=output_dir,
        )
        register_dataset(
            aoi.slug, "env", year,
            pathlib.Path(nc_result["env_path"]).name,
            type="time-series",
            variables=nc_result["variables"],
            format="nc",
            data_root=data_root,
        )
        dem_path = output_dir / f"{aoi.slug}_elevation.tif"
        water_path = output_dir / f"{aoi.slug}_water_occurrence.tif"
        land_path = output_dir / f"{aoi.slug}_land_mask.tif"
        if dem_path.exists() and water_path.exists():
            from .daily_nc import read_static_tif

            h, w = aoi.cells_per_side()
            dem_da = xr.DataArray(read_static_tif(dem_path, (h, w)), dims=("y", "x"))
            water_da = xr.DataArray(read_static_tif(water_path, (h, w)), dims=("y", "x"))
            dem_da.rio.write_crs(aoi.crs_obj, inplace=True)
            water_da.rio.write_crs(aoi.crs_obj, inplace=True)
            transform = from_bounds(*aoi.bbox, w, h)
            dem_da.rio.write_transform(transform, inplace=True)
            water_da.rio.write_transform(transform, inplace=True)

            # Open-ocean mask (1 = open ocean, 0 = land or coast). When absent,
            # we fall back to reading the buffered permanent_water_mask from
            # the NC: any cell NOT classified as permanent in the NC is
            # considered "could be pluvial" and the JRC-vs-land filtering
            # left those cells alone. Cells classified as permanent in the
            # NC live on land by construction (daily_nc applied the coast
            # filter).
            open_ocean_da = None
            if land_path.exists():
                land_da = xr.DataArray(
                    read_static_tif(land_path, (h, w)), dims=("y", "x")
                )
                land_da.rio.write_crs(aoi.crs_obj, inplace=True)
                land_da.rio.write_transform(transform, inplace=True)
                # land_mask is 1 inside the buffered coastline, 0 outside
                # (open ocean). For the exclusion rule we want "open ocean"
                # = where land==0.
                open_ocean_da = xr.DataArray(
                    (land_da.values < 0.5).astype(np.float32),
                    dims=("y", "x"),
                )
                open_ocean_da.rio.write_crs(aoi.crs_obj, inplace=True)
                open_ocean_da.rio.write_transform(transform, inplace=True)

            permanent_da = None
            # M12-fix (2026-08-26): we compute permanent_water_mask locally
            # from (raw JRC == 1.0) AND (land_mask == 1). This matches the
            # definition in daily_nc but uses the raw JRC TIF (which still
            # carries intermediate values for pluvial cells), so cells with
            # JRC in [0.05, 1.0) on land are correctly classified as pluvial.
            # The NC's permanent_water_mask is only present for JRC=1 cells
            # (post-filter, {0,1}-valued), which would classify every patch
            # as permanent — losing the pluvial tier.
            if open_ocean_da is not None:
                water_arr_norm = np.asarray(water_da.values, dtype=np.float32)
                # The raw JRC TIF is in [0, 100] percent; the daily_nc
                # pipeline normalises to [0, 1]. Align before thresholding.
                if water_arr_norm.max(initial=0.0) > 1.5:
                    water_arr_norm = water_arr_norm / 100.0
                is_jrc_permanent = water_arr_norm >= 1.0
                is_land = (
                    np.asarray(open_ocean_da.values, dtype=np.float32) < 0.5
                )
                perm_array = (is_jrc_permanent & is_land).astype(np.float32)
                permanent_da = xr.DataArray(perm_array, dims=("y", "x"))
                permanent_da.rio.write_crs(aoi.crs_obj, inplace=True)
                permanent_da.rio.write_transform(transform, inplace=True)
            else:
                nc_path = pathlib.Path(nc_result["env_path"])
                if nc_path.exists():
                    with xr.open_dataset(nc_path) as env_ds:
                        if "permanent_water_mask" in env_ds:
                            permanent_da = (
                                env_ds["permanent_water_mask"].isel(time=0).load()
                            )
                            permanent_da = permanent_da.rename({
                                permanent_da.dims[-2]: "y",
                                permanent_da.dims[-1]: "x",
                            })
                            permanent_da = permanent_da.rio.write_crs(aoi.crs_obj)
                            permanent_da = permanent_da.rio.write_transform(transform)
            habitat_path = output_dir / f"{aoi.slug}_habitat_patches.gpkg"
            _write_habitat_patches_gpkg(
                habitat_path, dem_da, water_da, aoi,
                twi_threshold=twi_threshold,
                permanent_mask=permanent_da,
                open_ocean_mask=open_ocean_da,
            )
            register_dataset(
                aoi.slug, "habitat", year, habitat_path.name,
                type="time-series", format="gpkg", data_root=data_root,
            )
            nc_result["habitat_path"] = str(habitat_path)
        return nc_result

    if isinstance(scale, str):
        scale = Scale(scale)
    h, w = aoi.cells_per_side()
    suffix = f"{aoi.slug}_{aoi.scale.value}_{year:04d}_{month:02d}"
    env_path = output_dir / f"{suffix}_env.tif"
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
        format="tif",
    )
    register_dataset(
        aoi.slug, "habitat", year,
        str(habitat_path.name),
        type="time-series",
    )

    return results
