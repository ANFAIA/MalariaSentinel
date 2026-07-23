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
    nodata: float = -9999.0,
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
        nodata: sentinel value to mask before summing (default -9999.0).

    Returns:
        (H_dst, W_dst) numpy array (float32).
    """
    from rasterio.warp import Resampling, reproject

    h_dst, w_dst = target_shape

    # Mask nodata before reproject to avoid summing sentinel values.
    source_masked = np.where(source == nodata, 0.0, source).astype(np.float32)
    dst = np.zeros((h_dst, w_dst), dtype=np.float32)

    resampling = Resampling.sum if method == "sum" else Resampling.nearest

    reproject(
        source=source_masked,
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
    pigs: np.ndarray | None = None,
    chickens: np.ndarray | None = None,
    building_fraction: np.ndarray | None = None,
    wildlife_host_proxy: np.ndarray | None = None,
) -> pathlib.Path:
    """Write the static host density NetCDF for the ABM engine.

    The NetCDF has 5 core data variables on (y, x), plus up to 4 optional:
        * ``human``               — persons per ABM cell (float32)
        * ``cattle``              — cattle per ABM cell (float32)
        * ``goats``               — goats per ABM cell (float32)
        * ``sheep``               — sheep per ABM cell (float32)
        * ``urban_class``         — settlement class code (int32: 30/50)
        * ``pigs``                — pigs per ABM cell (float32, optional)
        * ``chickens``            — chickens per ABM cell (float32, optional)
        * ``building_fraction``   — building footprint fraction [0,1] (float32, optional)
        * ``wildlife_host_proxy`` — wildlife host suitability [0,1] (float32, optional)

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
            "x": xr.DataArray(xs, dims="x", attrs={"axis": "X", "standard_name": "longitude", "units": "degrees_east"}),
            "y": xr.DataArray(ys, dims="y", attrs={"axis": "Y", "standard_name": "latitude", "units": "degrees_north"}),
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

    # Optional variables
    all_vars = ["human", "cattle", "goats", "sheep", "urban_class"]
    if pigs is not None:
        assert pigs.shape == (H, W), f"pigs shape {pigs.shape} != ({H}, {W})"
        ds["pigs"] = xr.DataArray(
            pigs.astype(np.float32), dims=("y", "x"),
            attrs={"long_name": "Pig count", "units": "animals/cell", "nodata": nodata},
        )
        all_vars.append("pigs")
    if chickens is not None:
        assert chickens.shape == (H, W), f"chickens shape {chickens.shape} != ({H}, {W})"
        ds["chickens"] = xr.DataArray(
            chickens.astype(np.float32), dims=("y", "x"),
            attrs={"long_name": "Chicken count", "units": "animals/cell", "nodata": nodata},
        )
        all_vars.append("chickens")
    if building_fraction is not None:
        assert building_fraction.shape == (H, W), f"building_fraction shape {building_fraction.shape} != ({H}, {W})"
        ds["building_fraction"] = xr.DataArray(
            building_fraction.astype(np.float32), dims=("y", "x"),
            attrs={"long_name": "Building footprint fraction", "units": "fraction [0,1]", "nodata": nodata},
        )
        all_vars.append("building_fraction")
    if wildlife_host_proxy is not None:
        assert wildlife_host_proxy.shape == (H, W), f"wildlife_host_proxy shape {wildlife_host_proxy.shape} != ({H}, {W})"
        ds["wildlife_host_proxy"] = xr.DataArray(
            wildlife_host_proxy.astype(np.float32), dims=("y", "x"),
            attrs={"long_name": "Wildlife host proxy suitability", "units": "suitability [0,1]", "nodata": nodata},
        )
        all_vars.append("wildlife_host_proxy")

    # Write CRS as a coordinate variable (CF convention)
    crs_var = xr.DataArray(
        np.int32(0),
        attrs={
            "grid_mapping_name": "transverse_mercator",
            "crs_wkt": str(grid_spec["crs"]),
        },
    )
    ds["crs"] = crs_var
    for var_name in all_vars:
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
    *,
    pigs: np.ndarray | None = None,
    chickens: np.ndarray | None = None,
    building_fraction: np.ndarray | None = None,
    wildlife_host_proxy: np.ndarray | None = None,
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

    # Optional variables
    if pigs is not None:
        manifest["variables"].append(_stats(pigs, "pigs"))
    if chickens is not None:
        manifest["variables"].append(_stats(chickens, "chickens"))
    if building_fraction is not None:
        manifest["variables"].append(_stats(building_fraction, "building_fraction"))
    if wildlife_host_proxy is not None:
        manifest["variables"].append(_stats(wildlife_host_proxy, "wildlife_host_proxy"))

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path
