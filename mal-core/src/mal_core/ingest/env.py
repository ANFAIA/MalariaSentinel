"""Ingest stage - build the daily env NetCDF + static habitat patches for an AOI.

Contract v3.0 of the proxy-habitat redesign
(docs/plans/in-process/redesign/02-oferta-criaderos-proxies-download-ingest-abm.md
§9): habitat patches are a STATIC cell union. Candidate cells are those
whose total potential (sum of the six H features from ``mal_core.habitat``,
computed by the canonical ``potential.static_potential``) is above a
documented numerical floor. The patch gpkg carries the six per-cell H
values plus their AMPLITUDE (+ the total used as the oviposition
attraction weight). No DEM, no TWI, no urban bar, no per-cell mm solver.
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

from ._shared import register_dataset


# -- helpers ----------------------------------------------------------------


def _read_static(path: pathlib.Path, aoi: AOI, var: str) -> np.ndarray:
    """Open a contract-v3.0 static NC and read a (H, W) float array."""
    with xr.open_dataset(path) as ds:
        if var not in ds:
            raise ValueError(
                f"{path} has no '{var}' variable; "
                f"vars={sorted(ds.data_vars)}"
            )
        arr = ds[var].values.astype(np.float32)
        if arr.ndim == 3:
            arr = arr[0]
        h, w = aoi.cells_per_side()
        if arr.shape != (h, w):
            raise ValueError(f"{path}.{var} shape {arr.shape} != AOI grid {(h, w)}")
        return np.nan_to_num(arr, nan=0.0)


def _write_habitat_patches_gpkg(
    path: pathlib.Path,
    statics: dict[str, np.ndarray],
    aoi: AOI,
) -> pathlib.Path:
    """Write the static candidate-cell union to a GeoPackage.

    Columns mirror contract v3.0 §9: the six H features (the mapping is a
    pure function of the jrc/wc statics via ``mal_core.habitat.potential``),
    the amplitude ``habitat_potential`` (sum of the six H values), a coarse
    ``hab_type`` label from the DYNAMICS dict (which temporal response the
    patch's dominant habitat type follows) and the (row, col) identity.
    No empty-column beacons like `twi_value`/`urban_capacity_factor` are
    written anymore; the C++ gpkg parser requires the H columns and
    reads the amplitude only for backward-observability of the new stack.
    """
    from mal_core.habitat import potential as _pot

    h_static = _pot.static_potential(statics)
    h_total = np.asarray(_pot.total_potential(h_static), dtype=np.float64)

    h, w = aoi.cells_per_side()
    rows, cols = np.where(h_total > 0.0)
    transform = from_bounds(*aoi.bbox, w, h)
    xs = transform.c + (cols + 0.5) * transform.a
    ys = transform.f + (rows + 0.5) * transform.e

    from mal_core.habitat.config import dynamics_map as _dynamics_map
    _dynamics = _dynamics_map()

    # Column per habitat type + total + labelled columns.
    #   hab_type: the dominant habitat type (argmax of the six H values)
    #   dynamics: that type's temporal class (persistent | pluvial)
    dominant_types = [
        max(_dynamics,
            key=lambda g: float(h_static[g][r, c]))
        for r, c in zip(rows, cols)
    ]
    data: dict[str, object] = {
        "hab_type": np.array(dominant_types),
        "dynamics": np.array(
            [_dynamics[g] for g in dominant_types]
        ),
        "habitat_potential": h_total[rows, cols],
        "row": rows.astype(np.int32),
        "col": cols.astype(np.int32),
        "aoi_slug": aoi.slug,
    }
    for g_name in h_static:
        data[f"hab_{g_name}"] = h_static[g_name][rows, cols]

    gdf = gpd.GeoDataFrame(
        data,
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
    data_root: pathlib.Path | None = None,
) -> dict:
    """Build the daily env NC + static habitat patches for an AOI.

    Delegates the NC build to the canonical builder in daily_nc.py, then
    derives the static candidate-cell gpkg from the statics the NC carry.

    Args:
        aoi: the AOI object or a string slug.
        year: year (metadata; the NC is multi-year daily).
        month: month 1-12 (metadata only).
        output_dir: directory containing the downloaded raw inputs; the NC
            and habitat patches are written here too.
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
        license="CHIRPS-Cite+Copernicus-Cite+CC-BY-4.0",
        attribution=(
            "Derived from CHIRPS v2 (Funk et al. 2014), JRC GSW v1.4 "
            "(© EU/JRC, CC BY 4.0), ERA5-Land (Contains modified Copernicus "
            "Climate Change Service information [Year]) and Google Dynamic "
            "World V1 (© Google, CC BY 4.0; contains modified Copernicus "
            "Sentinel data [Year])."
        ),
        data_root=data_root,
    )

    env_path = pathlib.Path(nc_result["env_path"])
    statics = {
        "jrc_persistent": _read_static(env_path, aoi, "jrc_persistent"),
        "lc_built": _read_static(env_path, aoi, "lc_built"),
        "lc_wetland": _read_static(env_path, aoi, "lc_wetland"),
        "lc_open_plus_water": _read_static(env_path, aoi, "lc_open_plus_water"),
        "lc_crop": _read_static(env_path, aoi, "lc_crop"),
    }
    habitat_path = output_dir / f"{aoi.slug}_habitat_patches.gpkg"
    _write_habitat_patches_gpkg(habitat_path, statics, aoi)
    register_dataset(
        aoi.slug, INGEST_ARTIFACTS["habitat"].key, year, habitat_path.name,
        type="time-series", format="gpkg",
        license="CC-BY-4.0",
        attribution=(
            "Derived from JRC GSW v1.4 (© EU/JRC, CC BY 4.0) and Google "
            "Dynamic World V1 (© Google, CC BY 4.0; contains modified "
            "Copernicus Sentinel data [Year])."
        ),
        variables=[
            "hab_type", "habitat_potential", "row", "col",
        ] + [f"hab_{g}" for g in statics],
        data_root=data_root,
    )
    nc_result["habitat_path"] = str(habitat_path)
    try:
        from mal_commonlib.data.licenses import warn_manifest_limits

        warn_manifest_limits(aoi.slug, data_root)
    except Exception as e:  # never break ingest over a warning
        logging.getLogger(__name__).debug("license warning skipped: %s", e)
    return nc_result
