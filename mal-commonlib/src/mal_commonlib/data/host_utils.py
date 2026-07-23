"""Host density utilities: grid aggregation and static NetCDF writer (M7).

Public surface
--------------
``aggregate_to_grid(source, source_transform, target_grid_spec, method="sum")``
    Conservatively aggregate a high-res source raster to a coarser ABM grid.

``build_host_static_nc(...)``
    Write the static host density NetCDF for the ABM engine.

Resampling rules:
    * Population / livestock: sum-preserving (conservative) aggregation.
    * Urban/rural classification: nearest-neighbour (categorical).

The ``target_grid_spec`` is a dict with keys ``crs``, ``transform``,
``height``, ``width`` describing the ABM grid.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np
import xarray as xr


def aggregate_to_grid(
    source: np.ndarray,
    source_transform: Any,
    source_crs: Any,
    target_transform: Any,
    target_crs: Any,
    target_shape: tuple[int, int],
    method: str = "sum",
) -> np.ndarray:
    """Aggregate a source raster to a target grid.

    Uses ``rasterio.warp.reproject`` under the hood. For ``method="sum"``
    the resampling is ``Resampling.sum`` (conservative / area-weighted).
    For ``method="nearest"`` it is ``Resampling.nearest`` (categorical).

    Args:
        source: (H_src, W_src) numpy array.
        source_transform: affine transform of the source.
        source_crs: CRS of the source (anything rasterio accepts).
        target_transform: affine transform of the target grid.
        target_crs: CRS of the target grid.
        target_shape: (H_dst, W_dst) of the target grid.
        method: "sum" (conservative) or "nearest" (categorical).

    Returns:
        (H_dst, W_dst) numpy array (float32).
    """
    from rasterio.warp import Resampling, reproject

    h_dst, w_dst = target_shape
    dst = np.zeros((h_dst, w_dst), dtype=np.float32)

    resampling = Resampling.sum if method == "sum" else Resampling.nearest

    reproject(
        source=source.astype(np.float32),
        destination=dst,
        src_transform=source_transform,
        src_crs=source_crs,
        dst_transform=target_transform,
        dst_crs=target_crs,
        resampling=resampling,
    )
    return dst


def build_host_static_nc(
    human: np.ndarray,
    cattle: np.ndarray,
    goats: np.ndarray,
    sheep: np.ndarray,
    urban_class: np.ndarray,
    output_path: pathlib.Path,
    grid_spec: dict,
    *,
    nodata: float = -9999.0,
) -> pathlib.Path:
    """Write the static host density NetCDF for the ABM engine.

    The NetCDF has 5 data variables on (y, x):
        * ``human``          — persons per ABM cell (float32)
        * ``cattle``         — cattle per ABM cell (float32)
        * ``goats``          — goats per ABM cell (float32)
        * ``sheep``          — sheep per ABM cell (float32)
        * ``urban_class``    — settlement class code (int32: 30/50)

    Global attributes include CRS WKT, grid transform, and nodata sentinel.

    Args:
        human: (H, W) human population count per cell.
        cattle: (H, W) cattle count per cell.
        goats: (H, W) goats count per cell.
        sheep: (H, W) sheep count per cell.
        urban_class: (H, W) GHS-SMOD class (30=urban, 50=rural).
        output_path: path to write the NetCDF.
        grid_spec: dict with ``crs`` (WKT/str), ``transform`` (affine),
                   ``height``, ``width``.
        nodata: sentinel for missing values.

    Returns:
        Path to the written NetCDF file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    H, W = human.shape
    assert cattle.shape == (H, W), f"cattle shape {cattle.shape} != ({H}, {W})"
    assert goats.shape == (H, W), f"goats shape {goats.shape} != ({H}, {W})"
    assert sheep.shape == (H, W), f"sheep shape {sheep.shape} != ({H}, {W})"
    assert urban_class.shape == (H, W), f"urban_class shape {urban_class.shape} != ({H}, {W})"

    # Build coordinate arrays from the transform
    transform = grid_spec["transform"]
    xs = np.array([transform.c + i * transform.a for i in range(W)], dtype=np.float64)
    ys = np.array([transform.f + j * transform.e for j in range(H)], dtype=np.float64)

    ds = xr.Dataset(
        {
            "human": xr.DataArray(
                human.astype(np.float32),
                dims=("y", "x"),
                attrs={"long_name": "Human population count", "units": "persons/cell", "nodata": nodata},
            ),
            "cattle": xr.DataArray(
                cattle.astype(np.float32),
                dims=("y", "x"),
                attrs={"long_name": "Cattle count", "units": "animals/cell", "nodata": nodata},
            ),
            "goats": xr.DataArray(
                goats.astype(np.float32),
                dims=("y", "x"),
                attrs={"long_name": "Goat count", "units": "animals/cell", "nodata": nodata},
            ),
            "sheep": xr.DataArray(
                sheep.astype(np.float32),
                dims=("y", "x"),
                attrs={"long_name": "Sheep count", "units": "animals/cell", "nodata": nodata},
            ),
            "urban_class": xr.DataArray(
                urban_class.astype(np.int32),
                dims=("y", "x"),
                attrs={
                    "long_name": "GHS-SMOD settlement class",
                    "units": "class code (30=urban, 50=rural)",
                    "nodata": -9999,
                },
            ),
        },
        coords={
            "x": xs,
            "y": ys,
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel static host density",
            "source_crs": str(grid_spec["crs"]),
            "grid_height": H,
            "grid_width": W,
            "nodata": nodata,
            "generated_by": "mal-commonlib build_hosts",
        },
    )

    # Write CRS as a coordinate variable (CF convention)
    crs_var = xr.DataArray(
        np.int32(0),
        attrs={
            "grid_mapping_name": "transverse_mercator",
            "crs_wkt": str(grid_spec["crs"]),
        },
    )
    ds["crs"] = crs_var
    for var_name in ["human", "cattle", "goats", "sheep", "urban_class"]:
        ds[var_name].attrs["grid_mapping"] = "crs"

    ds.to_netcdf(str(output_path), engine="netcdf4")
    return output_path


def write_manifest(
    output_path: pathlib.Path,
    human: np.ndarray,
    cattle: np.ndarray,
    goats: np.ndarray,
    sheep: np.ndarray,
    urban_class: np.ndarray,
    grid_spec: dict,
) -> pathlib.Path:
    """Write a JSON manifest describing the host static NetCDF.

    The manifest records summary statistics and grid metadata so that
    the ABM engine can validate inputs before reading the NetCDF.
    """
    manifest_path = output_path.parent / "host_manifest.json"
    H, W = human.shape

    def _stats(arr: np.ndarray, name: str) -> dict:
        valid = arr[arr != -9999.0]
        return {
            "variable": name,
            "shape": list(arr.shape),
            "min": float(valid.min()) if valid.size > 0 else 0.0,
            "max": float(valid.max()) if valid.size > 0 else 0.0,
            "mean": float(valid.mean()) if valid.size > 0 else 0.0,
            "total": float(valid.sum()) if valid.size > 0 else 0.0,
            "nodata_count": int((arr == -9999.0).sum()),
        }

    manifest = {
        "netcdf_path": str(output_path.name),
        "grid": {
            "crs": str(grid_spec["crs"]),
            "height": H,
            "width": W,
        },
        "variables": [
            _stats(human, "human"),
            _stats(cattle, "cattle"),
            _stats(goats, "goats"),
            _stats(sheep, "sheep"),
            _stats(urban_class.astype(np.float32), "urban_class"),
        ],
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path
