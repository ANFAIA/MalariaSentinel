"""Ingest stage - build the daily env NetCDF + habitat patches for an AOI.

The only output format is the daily multi-year NetCDF (M13+) consumed by
the C++ ABM via read_env_nc() in env_reader.cpp. The legacy 4-band monthly
COG (TIF) path was removed - see docs/specs/ingest/spec.md.
"""
from __future__ import annotations

import logging
import pathlib

import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI
from mal_commonlib.terrain.twi import compute_twi

from ._shared import register_dataset


# -- helpers ----------------------------------------------------------------


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
    twi_threshold: float = 8.0,
    data_root: pathlib.Path | None = None,
) -> dict:
    """Build the daily env NC + habitat patches for an AOI.

    Delegates the NC build to the canonical builder in daily_nc.py. This is
    the input format the C++ ABM actually reads via read_env_nc() in
    env_reader.cpp.

    Args:
        aoi: the AOI object or a string slug.
        year: year (e.g. 2024).
        month: month 1-12 (metadata only; the NC is multi-year daily).
        output_dir: directory containing the downloaded raw inputs; the NC
            and habitat patches are written here too.
        twi_threshold: TWI threshold for habitat patch detection.
        data_root: optional root for manifest registration (default: the
            conventional ``data/`` layout).

    Returns:
        dict with 'env_path', 'habitat_path', and other metadata.
    """
    if isinstance(aoi, str):
        aoi = AOI.from_slug(aoi)

    from .daily_nc import build_daily_env_nc
    from ..download.catalog import INGEST_ARTIFACTS
    nc_result = build_daily_env_nc(
        aoi=aoi.slug,
        data_dir=output_dir,
    )
    register_dataset(
        aoi.slug, INGEST_ARTIFACTS["env"].key, year,
        pathlib.Path(nc_result["env_path"]).name,
        type="time-series",
        variables=nc_result["variables"],
        format="nc",
        license=("Copernicus-Cite+CC-BY-4.0+CHIRPS-Cite"),
        attribution=(
            "Derived from CHIRPS v2 (Funk et al. 2014), JRC GSW v1.4 "
            "(© EU/JRC, CC BY 4.0), ERA5-Land (Contains modified Copernicus "
            "Climate Change Service information [Year]) and MODIS MOD13A3 "
            "(NASA LP DAAC)."
        ),
        data_root=data_root,
    )
    # Manifest-first resolution for the static rasters the habitat builder
    # re-reads — via the catalog, identity = manifest key (strict when a
    # declared file is missing; absent entry = the corresponding habitat
    # inputs degrade, as daily_nc documents).
    from ..download.catalog import resolve

    dem_path = resolve(aoi.slug, "dem", data_dir=output_dir)
    water_path = resolve(aoi.slug, "jrc_water", data_dir=output_dir)
    land_path = resolve(aoi.slug, "coastline_land_mask", data_dir=output_dir)
    if dem_path is not None and water_path is not None:
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
        if land_path is not None:
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
            aoi.slug, INGEST_ARTIFACTS["habitat"].key, year, habitat_path.name,
            type="time-series", format="gpkg",
            license="ODbL-1.0+CC-BY-4.0",
            attribution=(
                "Derived from MERIT DEM (Yamazaki Lab, ODbL 1.0 branch "
                "elected 2026-09-27) and JRC GSW (© EU/JRC, CC BY 4.0)."
            ),
            data_root=data_root,
        )
        nc_result["habitat_path"] = str(habitat_path)
    try:
        from mal_commonlib.data.licenses import warn_manifest_limits

        warn_manifest_limits(aoi.slug, data_root)
    except Exception as e:  # never break ingest over a warning
        logging.getLogger(__name__).debug("license warning skipped: %s", e)
    return nc_result
