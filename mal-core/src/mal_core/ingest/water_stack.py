"""Build M12 water-stack NetCDF from downloaded source products."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
import xarray as xr


def _read_static(path: Path, shape: tuple[int, int]) -> np.ndarray:
    with rasterio.open(path) as src:
        values = src.read(
            1,
            out_shape=shape,
            resampling=rasterio.enums.Resampling.nearest,
        ).astype(np.float32)
        if src.nodata is not None:
            values[np.isclose(values, src.nodata)] = np.nan
    return values


def _first(data_dir: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        candidates = sorted(data_dir.glob(pattern))
        if candidates:
            return candidates[0]
    return None


def build_water_stack(
    aoi: str,
    data_dir: Path,
    *,
    output_path: Path | None = None,
) -> Path:
    """Create ``<aoi>_water_stack.nc`` with source layers kept separate.

    Static water layers define a reproducible baseline stack. Optional source
    layers remain separate for diagnostics, while the ABM uses JRC and
    permanent hydrography as its water context.
    """
    data_dir = Path(data_dir)
    output_path = output_path or data_dir / f"{aoi}_water_stack.nc"
    static = _first(data_dir, [f"{aoi}_water_occurrence.tif", "*water_occurrence*.tif"])
    if static is None:
        raise FileNotFoundError(f"No JRC baseline found in {data_dir}")
    with rasterio.open(static) as src:
        shape = (src.height, src.width)
    values = np.zeros((1, *shape), dtype=np.float32)
    coords = {"time": np.array([np.datetime64("2024-01-01")])}

    baseline_path = _first(data_dir, [f"{aoi}_water_occurrence.tif", "*water_occurrence*.tif"])
    if baseline_path is None:
        raise FileNotFoundError(f"No JRC baseline found in {data_dir}")
    baseline = _read_static(baseline_path, shape)
    if np.nanmax(baseline) > 1:
        baseline = baseline / 100.0

    lakes = _first(data_dir, [f"{aoi}_permanent_lakes.tif"])
    rivers = _first(data_dir, [f"{aoi}_permanent_rivers.tif"])
    wc_water = _first(data_dir, [f"{aoi}_wc_permanent_water.tif"])
    permanent_sources = [
        _read_static(path, shape) for path in (lakes, rivers, wc_water) if path
    ]
    permanent = np.maximum.reduce(permanent_sources) if permanent_sources else np.zeros(shape, dtype=np.float32)
    wetland_path = _first(data_dir, [f"{aoi}_wc_wetland.tif"])
    wetland = _read_static(wetland_path, shape) if wetland_path else np.zeros(shape, dtype=np.float32)

    stack = xr.Dataset(
        {
            "water_frac_baseline": (("time", "y", "x"), np.broadcast_to(baseline, values.shape).copy()),
            "permanent_water_mask": (("time", "y", "x"), np.broadcast_to(np.nan_to_num(permanent), values.shape).copy()),
            "wetland_mask": (("time", "y", "x"), np.broadcast_to(np.nan_to_num(wetland), values.shape).copy()),
            "water_occurrence_climatology": (("time", "y", "x"), np.broadcast_to(baseline, values.shape).copy()),
        },
        coords={**coords, "y": np.arange(shape[0]), "x": np.arange(shape[1])},
        attrs={
            "aoi_slug": aoi,
            "title": f"M12 water stack for {aoi}",
            "baseline_source": "JRC GSW",
            "permanent_source": "HydroLAKES + HydroRIVERS + WorldCover",
            "water_policy": "JRC GSW occurrence plus permanent hydrography",
        },
    )
    stack.to_netcdf(output_path)
    return output_path


__all__ = ["build_water_stack"]
